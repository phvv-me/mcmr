use super::scope::ClassScope;

/// Structural classification and placement established from one class declaration.
pub(in crate::classes) struct ClassShape {
    pub(in crate::classes) is_plain: bool,
    pub(in crate::classes) is_declarative: bool,
    pub(in crate::classes) scope: ClassScope,
}
