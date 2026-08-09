use crate::protocol::Node;
use serde::{Deserialize, Serialize};
use std::ops::Deref;

mod usage;

use usage::ImportUsage;

/// Which module imported one binding and which nodes stand for it, over how it is used.
///
/// Nothing here is settable from outside, because the declaration, the binding and the module node
/// are three views of one import statement and a caller replacing any one of them alone would
/// describe an import that was never written.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ImportContext {
    #[serde(default, skip_serializing_if = "String::is_empty")]
    importer_module: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    declaration: Option<Node>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    binding: Option<Node>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    module_node: Option<Node>,
    #[serde(flatten)]
    usage: ImportUsage,
}

impl ImportContext {
    pub fn binding(&self) -> Option<&Node> {
        self.binding.as_ref()
    }

    pub fn declaration(&self) -> Option<&Node> {
        self.declaration.as_ref()
    }

    pub fn importer_module(&self) -> &str {
        &self.importer_module
    }

    pub fn module_node(&self) -> Option<&Node> {
        self.module_node.as_ref()
    }
}

impl Deref for ImportContext {
    type Target = ImportUsage;

    fn deref(&self) -> &Self::Target {
        &self.usage
    }
}
