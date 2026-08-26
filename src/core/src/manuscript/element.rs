/// One thing a markup reader met, in the order its file states it.
///
/// The variants are markup neutral on purpose. A LaTeX reader and a Typst reader disagree about
/// how a heading or a cross reference is spelled and agree about what one is, so the readers
/// differ and everything downstream, reading order included, is written once.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Element {
    /// Another file spliced into this one at this position.
    Include(String),
    /// A heading, at a level where zero is the outermost the document uses.
    Section { level: u8, title: String },
    /// The start of a named environment, whatever the environment turns out to be for.
    EnvironmentOpen(String),
    /// The end of a named environment.
    EnvironmentClose(String),
    /// A cross reference target declared here.
    Label(String),
    /// A cross reference to a target, and the command that spelled it.
    Reference { target: String, command: String },
    /// A bibliography reference, with the locator pinning the source when it carries one.
    Citation { key: String, pin: String },
    /// The caption of the float this sits inside.
    Caption(String),
    /// Mathematics, and whether it was set as a display rather than inline.
    Math { text: String, display: bool },
    /// Text the author marked, and the command that marked it.
    Emphasis { command: String, marked: String },
    /// A macro this document declares, naming a symbol the reader will meet spelled that way.
    Macro(String),
    /// An environment declared as a numbered statement, and whether it owes the reader a proof.
    StatementKind { name: String, owes_proof: bool },
    /// Ordinary running text.
    Text(String),
    /// The blank line or explicit break that ends a paragraph.
    ParagraphBreak,
    /// The explicit line break that ends one row of a table.
    RowBreak,
    /// The point past which the document is body rather than preamble.
    BodyStart,
}
