/// Where a module writes one class down.
///
/// A nested class is real inheritance the repository has to follow, and it is at the same time
/// unreachable from outside the module holding it, so every judgment about importing, exporting,
/// or moving a class reads this and stays with the declarations another module can actually name.
#[derive(Clone, Copy)]
pub(in crate::classes) enum ClassScope {
    Module,
    Nested,
}

impl ClassScope {
    /// Whether a class or a function holds this declaration rather than the module itself.
    pub(in crate::classes) fn is_nested(self) -> bool {
        matches!(self, Self::Nested)
    }
}
