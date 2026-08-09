use crate::protocol::Span as SourceSpan;

mod member;
mod scope;
mod shape;

pub(in crate::classes) use member::Member;
pub(in crate::classes) use scope::ClassScope;
pub(in crate::classes) use shape::ClassShape;

/// One class exactly as the file declaring it writes it down.
pub(in crate::classes) struct Declared {
    pub(in crate::classes) name: String,
    pub(in crate::classes) span: SourceSpan,
    pub(in crate::classes) bases: Vec<String>,
    pub(in crate::classes) line_count: usize,
    pub(in crate::classes) members: Vec<Member>,
    pub(in crate::classes) field_count: usize,
    pub(in crate::classes) shape: ClassShape,
}

impl Declared {
    /// Whether a class or a function holds this declaration rather than the module itself.
    pub(in crate::classes) fn is_nested(&self) -> bool {
        self.shape.scope.is_nested()
    }
}
