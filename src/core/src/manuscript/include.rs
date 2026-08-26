use super::located::Located;
use std::collections::BTreeMap;

/// One include, as the file that stated it would resolve it.
///
/// The directory and the target are named rather than passed in order, because both are ordinary
/// paths and a caller that swapped them would resolve every include to nothing without failing.
pub struct Include<'a> {
    pub directory: &'a str,
    pub target: &'a str,
}

impl Include<'_> {
    /// Return the repository path this include names, among the files actually read.
    ///
    /// TeX resolves an include against the directory it was written in and against the directory
    /// the build runs from, and the suffix is usually left off. Every spelling is tried, so an
    /// include naming nothing resolves to nothing and the reader simply meets no elements there.
    pub fn resolve(&self, read: &BTreeMap<String, Vec<Located>>) -> Option<String> {
        let named = self.target.trim().trim_start_matches("./");
        for base in [self.directory, ""] {
            let joined = match base.is_empty() {
                true => named.to_string(),
                false => format!("{base}/{named}"),
            };
            for candidate in [joined.clone(), format!("{joined}.tex")] {
                if read.contains_key(&candidate) {
                    return Some(candidate);
                }
            }
        }
        None
    }
}
