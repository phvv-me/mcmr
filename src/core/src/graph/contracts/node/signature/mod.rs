use super::parameter::NodeParameter;
use super::shape::NodeShape;
use serde::Serialize;
use std::ops::Deref;

/// What one callable or annotated declaration states, over the parameter facts under it.
#[derive(Clone, Debug, Default, Serialize)]
pub struct NodeSignature {
    #[serde(skip_serializing_if = "Option::is_none")]
    annotation: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    return_annotation: Option<String>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    decorators: Vec<String>,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    asynchronous: bool,
    #[serde(flatten)]
    parameter: NodeParameter,
}

impl NodeSignature {
    pub fn annotation(&self) -> Option<&str> {
        self.annotation.as_deref()
    }

    pub fn asynchronous(&self) -> bool {
        self.asynchronous
    }

    pub fn decorators(&self) -> &[String] {
        &self.decorators
    }

    pub fn return_annotation(&self) -> Option<&str> {
        self.return_annotation.as_deref()
    }

    pub(super) fn parameter(&mut self) -> &mut NodeParameter {
        &mut self.parameter
    }

    /// Take everything one declaration writes around itself in a single statement.
    pub(super) fn state(&mut self, shape: NodeShape) {
        self.annotation = shape.annotation;
        self.return_annotation = shape.return_annotation;
        self.decorators = shape.decorators;
        self.asynchronous = shape.asynchronous;
    }
}

impl Deref for NodeSignature {
    type Target = NodeParameter;

    fn deref(&self) -> &Self::Target {
        &self.parameter
    }
}
