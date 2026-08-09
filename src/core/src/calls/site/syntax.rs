use super::super::expression::Expression;
use crate::protocol::Node;
use serde::{Deserialize, Serialize};

/// The source structure written for one invocation.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct CallSyntax {
    pub(crate) path: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) arguments: Vec<Expression>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) keyword_names: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) receiver: Option<Expression>,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub(crate) assigned_target: String,
    pub(crate) node: Node,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) callee: Option<Node>,
}
