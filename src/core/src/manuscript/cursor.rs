/// A byte cursor over one document that keeps the line every read position sits on.
///
/// Markup is read lexically rather than parsed, because TeX has no grammar a scanner can settle
/// and Typst is worth reading the same way for one shared element stream. Carrying the line
/// beside the offset is what lets every emitted element name a place an editor can open.
#[derive(Clone)]
pub struct Cursor<'a> {
    text: &'a str,
    offset: usize,
    line: usize,
}

impl<'a> Cursor<'a> {
    pub fn new(text: &'a str) -> Self {
        Self {
            text,
            offset: 0,
            line: 1,
        }
    }

    /// Consume and return the next character.
    pub fn bump(&mut self) -> Option<char> {
        let found = self.peek()?;
        self.offset += found.len_utf8();
        if found == '\n' {
            self.line += 1;
        }
        Some(found)
    }

    /// Whether the whole document has been read.
    pub fn done(&self) -> bool {
        self.offset >= self.text.len()
    }

    /// Consume one exact prefix when it sits at the cursor, and say whether it did.
    pub fn eat(&mut self, prefix: &str) -> bool {
        if !self.rest().starts_with(prefix) {
            return false;
        }
        for _ in 0..prefix.chars().count() {
            self.bump();
        }
        true
    }

    /// The line the cursor currently sits on.
    pub fn line(&self) -> usize {
        self.line
    }

    /// The next character without consuming it.
    pub fn peek(&self) -> Option<char> {
        self.rest().chars().next()
    }

    /// The unread remainder of the document.
    pub fn rest(&self) -> &'a str {
        &self.text[self.offset..]
    }

    /// Consume everything up to one terminator, returning it without the terminator.
    ///
    /// Reaching the end of the document without meeting the terminator returns the remainder,
    /// because an unterminated span is a defect in the document rather than a reason to stop.
    pub fn take_until(&mut self, terminator: &str) -> String {
        let start = self.offset;
        while !self.done() && !self.rest().starts_with(terminator) {
            self.bump();
        }
        let taken = self.text[start..self.offset].to_string();
        self.eat(terminator);
        taken
    }

    /// Consume the run of characters satisfying one predicate.
    pub fn take_while(&mut self, wanted: impl Fn(char) -> bool) -> String {
        let start = self.offset;
        while self.peek().is_some_and(&wanted) {
            self.bump();
        }
        self.text[start..self.offset].to_string()
    }
}
