use crate::graph::{ImportingModule, absolute_module};
use crate::walk::walk;
use ruff_python_ast::{Alias, ModModule, Stmt};
use std::collections::BTreeMap;

/// The absolute name every name one module imports stands for.
///
/// `from ..types import kernel` in `pkg.stage.kernels` binds `kernel` to `pkg.types.kernel`, and
/// `import numba.cuda as gpu` binds `gpu` to `numba.cuda`, so a dotted name written against an
/// imported root reaches the absolute name its root stands for, followed by the rest it wrote.
#[derive(Clone, Debug, Default)]
pub(crate) struct ImportTargets(BTreeMap<String, String>);

impl ImportTargets {
    /// Read every import one module states, relative ones resolved against the importer.
    pub(crate) fn of(module: &ModModule, importer: ImportingModule<'_>) -> Self {
        Self(
            walk(module)
                .into_iter()
                .flat_map(|statement| Self::bound(statement, importer))
                .collect(),
        )
    }

    /// Return the absolute name a dotted name reaches when its root is one of these imports.
    pub(crate) fn reached(&self, dotted: &str) -> Option<String> {
        let (root, rest) = dotted.split_once('.').unwrap_or((dotted, ""));
        let target = self.0.get(root)?;
        Some(match rest {
            "" => target.clone(),
            rest => format!("{target}.{rest}"),
        })
    }

    /// Return the absolute name a dotted name written in this module reaches, itself when its root
    /// was never imported.
    pub(crate) fn resolve(&self, dotted: &str) -> String {
        self.reached(dotted).unwrap_or_else(|| dotted.to_string())
    }

    /// Return every name one statement imports, beside the absolute name it stands for.
    fn bound(statement: &Stmt, importer: ImportingModule<'_>) -> Vec<(String, String)> {
        match statement {
            Stmt::Import(item) => item.names.iter().map(Self::imported).collect(),
            Stmt::ImportFrom(item) => {
                let origin = absolute_module(importer, item);
                item.names
                    .iter()
                    .filter(|alias| alias.name.as_str() != "*")
                    .map(|alias| {
                        let name = alias.asname.as_ref().unwrap_or(&alias.name);
                        (name.to_string(), format!("{origin}.{}", alias.name))
                    })
                    .collect()
            }
            _ => Vec::new(),
        }
    }

    /// Return what one `import` binds, its alias for the whole path or else the path's root.
    fn imported(alias: &Alias) -> (String, String) {
        let imported = alias.name.as_str();
        match &alias.asname {
            Some(name) => (name.to_string(), imported.to_string()),
            None => {
                let root = imported.split('.').next().unwrap_or(imported);
                (root.to_string(), root.to_string())
            }
        }
    }
}
