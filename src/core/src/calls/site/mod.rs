use crate::protocol::Node;
use serde::{Deserialize, Serialize};

mod context;
mod syntax;
mod target;

use context::CallContext;
use syntax::CallSyntax;
use target::CallTarget;

/// One resolved invocation composed from target, syntax, and surrounding context.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct CallSite {
    #[serde(flatten)]
    pub(crate) target: CallTarget,
    #[serde(flatten)]
    pub(crate) syntax: CallSyntax,
    #[serde(flatten)]
    pub(crate) context: CallContext,
}

impl CallSite {
    /// Start one call with its provider-guaranteed name and addressed syntax node.
    pub fn new(qualified_name: String, node: Node) -> Self {
        let path = node.span.path.clone();
        Self {
            target: CallTarget {
                qualified_name,
                target_id: String::new(),
                is_external: false,
                is_standard_library: false,
                is_first_party: false,
                is_constructor: false,
            },
            syntax: CallSyntax {
                path,
                arguments: Vec::new(),
                keyword_names: Vec::new(),
                receiver: None,
                assigned_target: String::new(),
                node,
                callee: None,
            },
            context: CallContext::default(),
        }
    }

    pub(super) fn span_key(&self) -> (usize, usize, usize, usize) {
        (
            self.syntax.node.span.start_line,
            self.syntax.node.span.start_column,
            self.syntax.node.span.end_line,
            self.syntax.node.span.end_column,
        )
    }
}
