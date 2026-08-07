use crate::graph::contracts::{Export, Reference};

/// One module path read as the package that other modules may sit beneath.
#[derive(Clone, Copy)]
pub(super) struct Package<'a>(pub(super) &'a str);

impl Package<'_> {
    /// Whether one module is this package itself or a module nested inside it.
    pub(super) fn holds(self, module: &str) -> bool {
        module == self.0
            || module
                .strip_prefix(self.0)
                .is_some_and(|suffix| suffix.starts_with('.'))
    }
}

/// Whether one reference reaches an export from outside the facade that publishes it.
pub(super) fn outside_facade(export: &Export, reference: &Reference) -> bool {
    reference.location.path != export.path && !Package(&export.module).holds(&reference.module)
}
