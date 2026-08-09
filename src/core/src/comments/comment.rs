use super::kind::CommentKind;
use ruff_text_size::TextRange;

/// One located comment, in the shape a group reads it.
#[derive(Clone, Copy)]
pub(super) struct Comment<'a> {
    pub(super) range: TextRange,
    pub(super) text: &'a str,
    pub(super) kind: CommentKind,
}
