use super::comment::Comment;
use super::{dialect::Dialect, kind::CommentKind, text::body};
use crate::source::Source;
use ruff_text_size::TextRange;
use serde_json::{Value, json};

/// One run of comment lines that sit directly above one another.
pub(super) struct Group {
    last_line: usize,
    line_count: usize,
    character_count: usize,
    token_count: usize,
    body: String,
    kind: CommentKind,
    range: TextRange,
}

impl Group {
    /// Open one group on the comment that starts it, so a group always holds at least one line.
    pub(super) fn opened(source: &Source, comment: Comment<'_>) -> Self {
        Self {
            last_line: source.line_of(comment.range.end()),
            line_count: source.line_count(comment.range),
            character_count: comment.text.len(),
            token_count: comment.text.split_whitespace().count(),
            body: body(comment.text),
            kind: comment.kind,
            range: comment.range,
        }
    }

    /// Absorb one comment when it continues this group, and answer whether it did.
    ///
    /// A comment continues a group by sitting on the very next line under the same kind, and asking
    /// that here rather than at the caller is what keeps a non-adjacent comment from ever reaching
    /// the running totals. A directive and a sentence never join, even when they are adjacent,
    /// because the rules read the two for opposite reasons and a suppression absorbed into a
    /// paragraph would hide both.
    pub(super) fn absorbed(&mut self, source: &Source, comment: Comment<'_>) -> bool {
        if self.last_line + 1 != source.line_of(comment.range.start()) || self.kind != comment.kind
        {
            return false;
        }
        self.range = TextRange::new(self.range.start(), comment.range.end());
        self.last_line = source.line_of(comment.range.end());
        self.line_count += source.line_count(comment.range);
        self.character_count += comment.text.len();
        self.token_count += comment.text.split_whitespace().count();
        self.body.push('\n');
        self.body.push_str(&body(comment.text));
        true
    }

    pub(super) fn value(&self, source: &Source, dialect: &mut impl Dialect) -> Value {
        let (preceding_source, following_source) = source.neighbors(self.range, 3);
        json!({
            "text": self.body,
            "preceding_source": preceding_source,
            "following_source": following_source,
            "line_count": self.line_count,
            "character_count": self.character_count,
            "token_count": self.token_count,
            "parses_as_source": !self.kind.is_directive() && dialect.is_source(self.body.trim()),
            "is_directive": self.kind.is_directive(),
            "is_documentation": self.kind.is_documentation(),
            "node": source.node("comment", self.range),
        })
    }
}
