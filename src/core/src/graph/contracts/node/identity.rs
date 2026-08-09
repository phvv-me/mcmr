use super::super::{language::Language, node_kind::NodeKind, visibility::Visibility};
use super::location::NodeLocation;
use serde::Serialize;
use std::ops::Deref;

/// Who one declaration is, over where it was written.
#[derive(Clone, Debug, Serialize)]
pub struct NodeIdentity {
    id: String,
    kind: NodeKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    language: Option<Language>,
    visibility: Visibility,
    qualname: String,
    #[serde(flatten)]
    location: NodeLocation,
}

impl NodeIdentity {
    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn kind(&self) -> NodeKind {
        self.kind
    }

    pub fn language(&self) -> Option<Language> {
        self.language
    }

    pub fn qualname(&self) -> &str {
        &self.qualname
    }

    pub fn visibility(&self) -> Visibility {
        self.visibility
    }

    /// Name one declaration once, since its identifier is derived from the rest of this name.
    pub(super) fn new(
        id: String,
        kind: NodeKind,
        language: Option<Language>,
        visibility: Visibility,
        qualname: String,
    ) -> Self {
        Self {
            id,
            kind,
            language,
            visibility,
            qualname,
            location: NodeLocation::default(),
        }
    }

    pub(super) fn location(&mut self) -> &mut NodeLocation {
        &mut self.location
    }

    pub(super) fn narrow(&mut self, visibility: Visibility) {
        self.visibility = self.visibility.narrower(visibility);
    }

    pub(super) fn reach(&mut self, visibility: Visibility) {
        self.visibility = visibility;
    }
}

impl Deref for NodeIdentity {
    type Target = NodeLocation;

    fn deref(&self) -> &Self::Target {
        &self.location
    }
}
