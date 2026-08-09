use super::{
    datatype_kind::DatatypeKind, language::Language, node_kind::NodeKind, visibility::Visibility,
};
use serde::Serialize;
use std::ops::Deref;

mod binding;
mod identity;
mod location;
mod parameter;
mod placement;
mod role;
mod shape;
mod signature;

use identity::NodeIdentity;

pub use binding::NodeBinding;
pub use placement::NodePlacement;
pub use shape::NodeShape;

/// One declaration in the repository graph, named once and then described a facet at a time.
///
/// Everything under this node is private and readable only, because the identifier is derived from
/// the name and kind beside it and must never stop agreeing with them. A frontend therefore states
/// a whole facet at once rather than reaching past the node into the layer that holds one field of
/// it, which is what kept a half-stated parameter or a stale identifier representable before.
#[derive(Clone, Debug, Serialize)]
pub struct Node {
    #[serde(flatten)]
    identity: NodeIdentity,
}

impl Node {
    /// Declare one graph node with neutral optional language evidence.
    pub fn new(
        id: String,
        kind: NodeKind,
        language: Option<Language>,
        visibility: Visibility,
        qualname: String,
    ) -> Self {
        Self {
            identity: NodeIdentity::new(id, kind, language, visibility, qualname),
        }
    }

    /// State how this parameter binds, which the frontend reads off its own calling convention.
    pub fn binds(mut self, binding: NodeBinding) -> Self {
        self.identity
            .location()
            .signature()
            .parameter()
            .bind(binding);
        self
    }

    /// Mark a class node with the exact role its language frontend parsed.
    pub fn datatype(mut self, kind: DatatypeKind) -> Self {
        self.identity
            .location()
            .signature()
            .parameter()
            .role()
            .state(kind);
        self
    }

    /// Place this declaration in the file that writes it.
    pub fn declared(mut self, placement: NodePlacement) -> Self {
        self.identity.location().place(placement);
        self
    }

    /// Raise this declaration to public, which is what a later export statement does to it.
    pub fn exported(&mut self) {
        self.identity.reach(Visibility::Public);
    }

    /// Narrow this node's reach to the stricter of what two files declared about it.
    pub fn narrow(&mut self, visibility: Visibility) {
        self.identity.narrow(visibility);
    }

    /// Mark this module as the one its own directory is named after.
    pub fn packaged(mut self) -> Self {
        self.identity.location().package();
        self
    }

    /// State how far this declaration reaches.
    pub fn reached(mut self, visibility: Visibility) -> Self {
        self.identity.reach(visibility);
        self
    }

    /// State the annotations, decorators, and awaiting this declaration writes around itself.
    pub fn shaped(mut self, shape: NodeShape) -> Self {
        self.identity.location().signature().state(shape);
        self
    }
}

impl Deref for Node {
    type Target = NodeIdentity;

    fn deref(&self) -> &Self::Target {
        &self.identity
    }
}
