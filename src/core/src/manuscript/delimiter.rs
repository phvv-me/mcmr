use super::cursor::Cursor;

/// One pair of grouping characters a markup language delimits an argument with.
///
/// Nesting is counted rather than matched by a first-close scan, since a group holding another
/// group is ordinary in every markup language here and a first-close scan would truncate it.
/// Naming the pair once also stops a caller transposing the open and the close character.
#[derive(Clone, Copy)]
pub struct Delimiter {
    open: char,
    close: char,
}

/// The `{}` group every TeX control sequence takes its arguments in.
pub const BRACE: Delimiter = Delimiter {
    open: '{',
    close: '}',
};

/// The `[]` group an optional argument or a citation locator arrives in.
pub const BRACKET: Delimiter = Delimiter {
    open: '[',
    close: ']',
};

impl Delimiter {
    /// Consume one balanced group at the cursor, or nothing when no group opens there.
    pub fn read(self, cursor: &mut Cursor<'_>) -> Option<String> {
        if cursor.peek() != Some(self.open) {
            return None;
        }
        cursor.bump();
        let mut content = String::new();
        let mut depth = 1usize;
        while let Some(character) = cursor.bump() {
            if character == '\\' {
                content.push(character);
                content.extend(cursor.bump());
                continue;
            }
            depth = self.depth_after(character, depth);
            if depth == 0 {
                return Some(content);
            }
            content.push(character);
        }
        Some(content)
    }

    /// Return the nesting depth one character leaves behind it.
    fn depth_after(self, character: char, depth: usize) -> usize {
        match character {
            _ if character == self.open => depth + 1,
            _ if character == self.close => depth - 1,
            _ => depth,
        }
    }
}
