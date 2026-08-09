use crate::graph::contracts::{Node, NodeKind};
use std::collections::{BTreeMap, BTreeSet};

/// The names a reference is allowed to land on once every file has stated its declarations.
///
/// An import may only name a module while every other reference may name any declared symbol, so
/// the two sets are gathered once and answered from for the whole resolution pass.
pub(super) struct Reachable {
    pub(super) symbols: BTreeSet<String>,
    pub(super) modules: BTreeSet<String>,
}

impl Reachable {
    /// Gather both name sets from the declared nodes in one pass each.
    pub(super) fn of(nodes: &BTreeMap<String, Node>) -> Self {
        Self {
            symbols: nodes
                .values()
                .filter(|node| !node.kind().is_path_entity() && node.kind() != NodeKind::Parameter)
                .map(|node| node.qualname().to_string())
                .collect(),
            modules: nodes
                .values()
                .filter(|node| node.kind() == NodeKind::Module)
                .map(|node| node.qualname().to_string())
                .collect(),
        }
    }
}
