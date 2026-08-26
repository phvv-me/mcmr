/// What one named environment is for, as far as any markup language is concerned.
///
/// Whether an environment is a numbered statement is not decided here, because a document
/// declares its own statement environments and a fixed list would miss every one of them. What
/// is fixed is the handful of roles a reader can name without reading the preamble.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// Mathematics set as a display, whose body is read as one math span.
    Math,
    /// Literal text, whose body is not prose and is never scanned for anything.
    Verbatim,
    /// The proof of whatever numbered statement precedes it.
    Proof,
    /// A figure float, referenced by label rather than met in reading order.
    Figure,
    /// A table float, whose cells hold numbers the prose is expected to agree with.
    Table,
    /// The tabular body of a table, which is where those cells actually live.
    Cells,
    /// Anything else, including the document body and every statement environment.
    Other,
}

const MATH: &[&str] = &[
    "align",
    "alignat",
    "displaymath",
    "eqnarray",
    "equation",
    "flalign",
    "gather",
    "math",
    "multline",
    "split",
];

const VERBATIM: &[&str] = &[
    "Verbatim",
    "lstlisting",
    "minted",
    "tikzpicture",
    "verbatim",
];

const FIGURE: &[&str] = &["figure", "subfigure", "wrapfigure"];

const TABLE: &[&str] = &["table", "wraptable"];

const CELLS: &[&str] = &["longtable", "tabular", "tabularx", "tabulary"];

impl Role {
    /// Return the role one environment name carries, ignoring a starred spelling.
    pub fn of(kind: &str) -> Self {
        let base = kind.trim_end_matches('*');
        for (names, role) in [
            (MATH, Self::Math),
            (VERBATIM, Self::Verbatim),
            (FIGURE, Self::Figure),
            (TABLE, Self::Table),
            (CELLS, Self::Cells),
        ] {
            if names.contains(&base) {
                return role;
            }
        }
        if base == "proof" {
            Self::Proof
        } else {
            Self::Other
        }
    }

    /// The float kind this environment is, when it is one.
    pub fn float(self) -> Option<&'static str> {
        match self {
            Self::Figure => Some("figure"),
            Self::Table => Some("table"),
            _ => None,
        }
    }

    /// Whether this environment's body is read whole rather than scanned as prose.
    pub fn is_raw(self) -> bool {
        matches!(self, Self::Math | Self::Verbatim)
    }
}
