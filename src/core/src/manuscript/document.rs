use super::element::Element;
use super::include::Include;
use super::latex::LatexReader;
use super::located::Located;
use super::typst::TypstReader;
use crate::lexical::{Corpus, CorpusFile};
use std::collections::{BTreeMap, BTreeSet};

/// One manuscript, flattened into the order a reader meets it in.
///
/// A paper is written across many files and read as one. Reading order is the single thing every
/// rule in this family depends on, so it is established once here, by splicing each included file
/// in at the position that included it, rather than rediscovered by every rule from spans.
pub struct Manuscript {
    pub root: String,
    pub language: String,
    pub elements: Vec<Located>,
}

/// The suffixes a manuscript is written in, and the language each one names.
const MARKUP: &[(&str, &str)] = &[(".tex", "latex"), (".typ", "typst")];

impl Manuscript {
    /// A named proof imports the hypotheses of the statement explicitly named in its heading.
    pub(super) fn proof_target(&self, order: usize) -> Option<&str> {
        self.elements
            .iter()
            .skip(order + 1)
            .take_while(|located| {
                !matches!(
                    located.element,
                    Element::Text(_)
                        | Element::Math { .. }
                        | Element::ParagraphBreak
                        | Element::EnvironmentClose(_)
                )
            })
            .find_map(|located| match &located.element {
                Element::Reference { target, .. } => Some(target.as_str()),
                _ => None,
            })
    }
    /// Return every manuscript one repository holds, in path order.
    ///
    /// A root is a file that declares a document class, since that is the file a build is pointed
    /// at. Everything else is reachable from one, and a markup file no root includes is a fragment
    /// nobody reads on its own, so it produces no manuscript rather than a fake one.
    pub fn scan(
        root: &std::path::Path,
        scope: &crate::discovery::Scope,
    ) -> Result<Vec<Self>, String> {
        let corpus = Corpus::read(root, scope, Self::is_markup)?;
        let read: BTreeMap<String, Vec<Located>> = corpus
            .files()
            .iter()
            .map(|file| {
                let elements = if file.path.ends_with(".typ") {
                    TypstReader::read(file)?
                } else {
                    LatexReader::read(file)
                };
                Ok((file.path.clone(), elements))
            })
            .collect::<Result<_, String>>()?;
        let included = Self::included_typst(&read)?;
        Ok(corpus
            .files()
            .iter()
            .filter(|file| {
                file.text.contains("\\documentclass")
                    || (file.path.ends_with(".typ")
                        && !included.contains(&file.path)
                        && read[&file.path].iter().any(|located| {
                            matches!(located.element, Element::Section { .. } | Element::Text(_))
                        }))
            })
            .map(|file| Self::assembled(file, &read))
            .collect())
    }

    fn included_typst(read: &BTreeMap<String, Vec<Located>>) -> Result<BTreeSet<String>, String> {
        let mut included = BTreeSet::new();
        for (path, elements) in read.iter().filter(|(path, _)| path.ends_with(".typ")) {
            let directory = path.rsplit_once('/').map_or("", |(head, _)| head);
            for located in elements {
                if let Element::Include(target) = &located.element {
                    let resolved =
                        Include { directory, target }.resolve(read).ok_or_else(|| {
                            format!("{path}:{}: unresolved Typst include {target}", located.line)
                        })?;
                    included.insert(resolved);
                }
            }
        }
        Ok(included)
    }

    /// Flatten one root and everything it includes into a single reading order.
    fn assembled(file: &CorpusFile, read: &BTreeMap<String, Vec<Located>>) -> Self {
        let mut elements = Vec::new();
        let mut visited = vec![file.path.clone()];
        Self::splice(&file.path, read, &mut visited, &mut elements);
        Self::resolve_headings(&mut elements);
        Self {
            root: file.path.clone(),
            language: Self::language_of(&file.path).to_string(),
            elements,
        }
    }

    /// Resolve preamble heading aliases at their call sites, including in imported chapters.
    fn resolve_headings(elements: &mut [Located]) {
        let mut headings = BTreeMap::new();
        for located in elements {
            match &located.element {
                Element::HeadingMacro {
                    name,
                    level,
                    title,
                    replace,
                } => {
                    if *replace || !headings.contains_key(name) {
                        headings.insert(name.clone(), (*level, title.clone()));
                    }
                }
                Element::MacroUse(name) => {
                    if let Some((level, title)) = headings.get(name) {
                        located.element = Element::Section {
                            level: *level,
                            title: title.clone(),
                        };
                    }
                }
                _ => {}
            }
        }
    }

    /// Whether one path is markup this reader has a frontend for.
    fn is_markup(path: &str) -> bool {
        MARKUP.iter().any(|(suffix, _)| path.ends_with(suffix))
    }

    /// Return the markup language one path is written in.
    fn language_of(path: &str) -> &'static str {
        MARKUP
            .iter()
            .find(|(suffix, _)| path.ends_with(suffix))
            .map_or("latex", |(_, language)| language)
    }

    /// Copy one file's elements into the reading order, following every include it states.
    fn splice(
        path: &str,
        read: &BTreeMap<String, Vec<Located>>,
        visited: &mut Vec<String>,
        into: &mut Vec<Located>,
    ) {
        let Some(elements) = read.get(path) else {
            return;
        };
        let directory = path.rsplit_once('/').map_or("", |(head, _)| head);
        for located in elements {
            let Element::Include(target) = &located.element else {
                into.push(located.clone());
                continue;
            };
            let include = Include { directory, target };
            let Some(resolved) = include.resolve(read) else {
                continue;
            };
            if visited.contains(&resolved) {
                continue;
            }
            visited.push(resolved.clone());
            Self::splice(&resolved, read, visited, into);
        }
    }
}
