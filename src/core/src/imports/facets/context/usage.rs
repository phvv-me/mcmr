use crate::protocol::Node;
use serde::{Deserialize, Serialize};

/// How widely one imported binding is actually used where it was imported.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ImportUsage {
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    references: Vec<Node>,
    #[serde(default, skip_serializing_if = "is_zero")]
    relative_level: usize,
    #[serde(default, skip_serializing_if = "is_zero")]
    reference_count: usize,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    has_qualifying_use: bool,
}

impl ImportUsage {
    pub fn has_qualifying_use(&self) -> bool {
        self.has_qualifying_use
    }

    pub fn reference_count(&self) -> usize {
        self.reference_count
    }

    pub fn references(&self) -> &[Node] {
        &self.references
    }

    pub fn relative_level(&self) -> usize {
        self.relative_level
    }
}

fn is_zero(value: &usize) -> bool {
    *value == 0
}
