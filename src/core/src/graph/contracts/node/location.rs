use super::placement::NodePlacement;
use super::signature::NodeSignature;
use serde::Serialize;
use std::ops::Deref;

/// Where one declaration was written, over the signature it states there.
#[derive(Clone, Debug, Default, Serialize)]
pub struct NodeLocation {
    #[serde(skip_serializing_if = "Option::is_none")]
    path: Option<String>,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    is_package: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    line: Option<usize>,
    #[serde(skip)]
    source: Option<String>,
    #[serde(flatten)]
    signature: NodeSignature,
}

impl NodeLocation {
    pub fn is_package(&self) -> bool {
        self.is_package
    }

    pub fn line(&self) -> Option<usize> {
        self.line
    }

    pub fn path(&self) -> Option<&str> {
        self.path.as_deref()
    }

    pub fn source(&self) -> Option<&str> {
        self.source.as_deref()
    }

    pub(super) fn package(&mut self) {
        self.is_package = true;
    }

    /// Put this declaration in the file that writes it, at the line that writes it.
    pub(super) fn place(&mut self, placement: NodePlacement) {
        self.path = Some(placement.path);
        self.line = placement.line;
        self.source = placement.source;
    }

    pub(super) fn signature(&mut self) -> &mut NodeSignature {
        &mut self.signature
    }
}

impl Deref for NodeLocation {
    type Target = NodeSignature;

    fn deref(&self) -> &Self::Target {
        &self.signature
    }
}
