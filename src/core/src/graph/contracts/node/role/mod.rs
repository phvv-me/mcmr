use super::super::datatype_kind::DatatypeKind;
use serde::Serialize;

/// What one class-like declaration is beyond being a class.
#[derive(Clone, Debug, Default, Serialize)]
pub struct NodeRole {
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    is_abstract: bool,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    is_enum: bool,
}

impl NodeRole {
    pub fn is_abstract(&self) -> bool {
        self.is_abstract
    }

    pub fn is_enum(&self) -> bool {
        self.is_enum
    }

    /// Take the single role one parsed datatype states, so the two flags cannot disagree.
    pub(super) fn state(&mut self, kind: DatatypeKind) {
        self.is_abstract = kind == DatatypeKind::Contract;
        self.is_enum = kind == DatatypeKind::Enumeration;
    }
}
