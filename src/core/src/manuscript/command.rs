/// What one TeX control sequence does to the element stream.
///
/// Grouping the several hundred names a manuscript uses into a dozen behaviours is what keeps the
/// reader small. A command the list does not name contributes a word boundary and nothing else,
/// and its braces are walked into rather than consumed, so `\qmeas{0.4332}` still reads as the
/// number a rule about prose evidence has to see.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Command {
    /// `\begin`, opening a named environment.
    EnvironmentOpen,
    /// `\end`, closing a named environment.
    EnvironmentClose,
    /// A heading at one outline level.
    Section(u8),
    /// `\label`, declaring a cross reference target.
    Label,
    /// A cross reference command, whose own name tells a reader how it will print.
    Reference,
    /// A bibliography reference, optionally pinned by bracketed locators.
    Citation,
    /// `\input` or `\include`, splicing another file in at this position.
    Include,
    /// `\caption`, whose text belongs to the surrounding float.
    Caption,
    /// `\newtheorem`, declaring one numbered statement environment.
    StatementKind,
    /// `\theoremstyle`, deciding whether the next declarations owe a proof.
    StatementStyle,
    /// A macro declaration, naming a symbol the reader will meet spelled that way.
    Macro,
    /// Text the author marked, which is how a defined term is usually introduced.
    Emphasis,
    /// A command whose first group is presentation rather than prose.
    Discarded,
    /// Anything else, which separates words and contributes none of its own.
    Plain,
}

const SECTIONS: &[&str] = &[
    "part",
    "chapter",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
];

const REFERENCES: &[&str] = &[
    "Cref",
    "Crefrange",
    "autoref",
    "cref",
    "crefrange",
    "eqref",
    "nameref",
    "pageref",
    "ref",
];

const CITATIONS: &[&str] = &[
    "cite",
    "citealp",
    "citealt",
    "citeauthor",
    "citep",
    "citet",
    "citeyear",
    "citeyearpar",
];

const MACROS: &[&str] = &[
    "DeclareMathOperator",
    "newcommand",
    "providecommand",
    "renewcommand",
];

const EMPHASIS: &[&str] = &["emph", "term", "textbf", "textit", "textsc", "underline"];

const DISCARDED: &[&str] = &[
    "addcontentsline",
    "addtolength",
    "colorbox",
    "definecolor",
    "documentclass",
    "graphicspath",
    "hspace",
    "includegraphics",
    "setcounter",
    "setlength",
    "textcolor",
    "usepackage",
    "vspace",
];

impl Command {
    /// Return what one control sequence name does, ignoring a starred spelling.
    pub fn of(name: &str) -> Self {
        if let Some(level) = SECTIONS.iter().position(|section| *section == name) {
            return Self::Section(u8::try_from(level).unwrap_or(u8::MAX));
        }
        for (names, command) in [
            (REFERENCES, Self::Reference),
            (CITATIONS, Self::Citation),
            (MACROS, Self::Macro),
            (EMPHASIS, Self::Emphasis),
            (DISCARDED, Self::Discarded),
        ] {
            if names.contains(&name) {
                return command;
            }
        }
        Self::named(name)
    }

    /// Return the commands whose behaviour is one name rather than a family.
    fn named(name: &str) -> Self {
        match name {
            "begin" => Self::EnvironmentOpen,
            "end" => Self::EnvironmentClose,
            "label" => Self::Label,
            "input" | "include" => Self::Include,
            "caption" => Self::Caption,
            "newtheorem" => Self::StatementKind,
            "theoremstyle" => Self::StatementStyle,
            _ => Self::Plain,
        }
    }
}
