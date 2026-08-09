use super::super::parameter_kind::ParameterKind;
use super::binding::NodeBinding;
use super::role::NodeRole;
use serde::Serialize;
use std::ops::Deref;

/// How one parameter binds, over the role the declaration under it plays.
#[derive(Clone, Debug, Default, Serialize)]
pub struct NodeParameter {
    #[serde(skip_serializing_if = "Option::is_none")]
    ordinal: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    parameter_kind: Option<ParameterKind>,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    has_default: bool,
    #[serde(flatten)]
    role: NodeRole,
}

impl NodeParameter {
    pub fn has_default(&self) -> bool {
        self.has_default
    }

    pub fn ordinal(&self) -> Option<usize> {
        self.ordinal
    }

    pub fn parameter_kind(&self) -> Option<ParameterKind> {
        self.parameter_kind
    }

    /// Take a whole calling convention at once, so a position never arrives without its kind.
    pub(super) fn bind(&mut self, binding: NodeBinding) {
        self.ordinal = Some(binding.ordinal);
        self.parameter_kind = Some(binding.kind);
        self.has_default = binding.has_default;
    }

    pub(super) fn role(&mut self) -> &mut NodeRole {
        &mut self.role
    }
}

impl Deref for NodeParameter {
    type Target = NodeRole;

    fn deref(&self) -> &Self::Target {
        &self.role
    }
}
