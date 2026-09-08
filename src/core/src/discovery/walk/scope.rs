use super::entry_kind::EntryKind;
use crate::protocol::Request;
use ignore::{IncrementalIgnore, WalkBuilder};
use std::path::{Component, Path, PathBuf};
use std::sync::Mutex;

/// Which files one request is about, which every pass asks rather than only the walk.
///
/// The walk is not the only thing that reads a repository. The cross-language scan, the route
/// scan, and the history pass each open their own view of the tree, and a caller who narrowed the
/// request meant all of them. Compiling the answer once and handing it to each keeps Git ignores
/// and requested suffixes identical for source, history, routes, and cross-language evidence.
pub struct Scope {
    ignored: Mutex<IncrementalIgnore>,
    prefix: PathBuf,
    suffixes: Vec<String>,
    boundaries: Vec<PathBuf>,
}

impl Scope {
    /// Read the repository's Git ignore contract beside the requested source suffixes.
    pub fn of(root: &Path, suffixes: &[String]) -> Self {
        let scan_root = std::fs::canonicalize(root).unwrap_or_else(|_| root.to_path_buf());
        let contract_root = scan_root
            .ancestors()
            .find(|ancestor| ancestor.join(".gitignore").is_file())
            .unwrap_or(scan_root.as_path());
        let prefix = scan_root
            .strip_prefix(contract_root)
            .unwrap_or(Path::new(""))
            .to_path_buf();
        let mut walk = WalkBuilder::new(contract_root);
        walk.standard_filters(false)
            .parents(false)
            .git_ignore(true)
            .require_git(false);
        let ignored = walk
            .build_matchers()
            .pop()
            .expect("one discovery root always yields one matcher");
        Self {
            ignored: Mutex::new(ignored),
            prefix,
            suffixes: suffixes.to_vec(),
            boundaries: Vec::new(),
        }
    }

    /// Apply explicit nested-owner boundaries without reducing the owner's caller graph.
    pub fn requested(request: &Request) -> Result<Self, String> {
        let root = Path::new(&request.root);
        let mut scope = Self::of(root, &request.suffixes);
        if request.boundaries.is_empty() {
            return Ok(scope);
        }
        let canonical_root = root
            .canonicalize()
            .map_err(|failure| format!("analysis root could not be resolved: {failure}"))?;
        for boundary in &request.boundaries {
            let path = Path::new(boundary);
            if boundary.is_empty()
                || path
                    .components()
                    .any(|component| !matches!(component, Component::Normal(_)))
                || path.components().next().is_none()
            {
                return Err(format!(
                    "owner boundary {boundary:?} must be a nonempty root-relative directory without dot or parent components"
                ));
            }
            let canonical = root.join(path).canonicalize().map_err(|failure| {
                format!("owner boundary {boundary:?} could not be resolved: {failure}")
            })?;
            if !canonical.is_dir()
                || canonical == canonical_root
                || canonical != canonical_root.join(path)
            {
                return Err(format!(
                    "owner boundary {boundary:?} must name a directory inside the analysis root without symbolic-link aliases"
                ));
            }
            scope.boundaries.push(path.to_path_buf());
        }
        scope.boundaries.sort();
        scope.boundaries.dedup();
        Ok(scope)
    }

    /// Whether a path is owned by a separately analyzed nested project.
    pub fn crosses_boundary(&self, relative: &str) -> bool {
        self.boundaries
            .iter()
            .any(|boundary| Path::new(relative).starts_with(boundary))
    }

    /// Whether the exclusion set removes one path.
    pub fn excludes(&self, relative: &str) -> bool {
        self.is_ignored(relative, EntryKind::File)
    }

    /// Whether the exclusion set removes one directory, which is what lets a walk skip its subtree.
    ///
    /// A pattern that excludes a directory is written for the paths inside it, the way
    /// `**/target/**` is, so the directory is matched as the prefix its own contents carry rather
    /// than as a bare name that no such pattern would ever hit. The scan root itself is never
    /// excluded, since a walk that skipped it would read nothing at all.
    pub fn excludes_directory(&self, relative: &str) -> bool {
        !relative.is_empty() && self.is_ignored(relative, EntryKind::Directory)
    }

    /// Whether one repository-relative path is source this request asked to read.
    pub fn holds(&self, relative: &str) -> bool {
        !self.excludes(relative)
            && self
                .suffixes
                .iter()
                .any(|suffix| relative.ends_with(suffix.as_str()))
    }

    fn contract_path(&self, relative: &str) -> PathBuf {
        self.prefix.join(relative)
    }

    /// Whether one path is excluded, which the Git history always is and the ignore contract may be.
    fn is_ignored(&self, relative: &str, kind: EntryKind) -> bool {
        if self.crosses_boundary(relative) {
            return true;
        }
        if relative.split('/').any(|component| component == ".git") {
            return true;
        }
        let mut matcher = self
            .ignored
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        matcher
            .matched(self.contract_path(relative), kind.is_directory())
            .is_ignore()
    }
}

#[cfg(test)]
mod tests {
    use super::Scope;

    #[test]
    fn a_nested_scan_inherits_the_repository_ignore_contract() {
        let root = tempfile::tempdir().expect("a temporary repository must open");
        let repository = root.path().join("repository");
        std::fs::create_dir(&repository).expect("the repository must be writable");
        std::fs::write(repository.join(".gitignore"), "__pycache__/\n")
            .expect("the ignore contract must be writable");
        let nested = repository.join("src/package");
        std::fs::create_dir_all(&nested).expect("the nested scan root must be writable");

        assert!(Scope::of(&nested, &[".py".to_string()]).excludes_directory("__pycache__"));
    }
}
