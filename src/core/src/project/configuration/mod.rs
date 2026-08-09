use crate::discovery::Document;
use crate::protocol::JsonObject;
use serde_json::{Value, json};
use toml::Table;

use super::fact_identity::FactIdentity;

mod assignments;
mod python_target;
mod test_suite;
mod text;

use assignments::configuration_assignments;
use python_target::python_target;

#[cfg(test)]
pub(super) use python_target::minor;
pub(super) use test_suite::test_suite;

/// State what a repository configures about itself, which is its policy and its Python target.
pub(super) fn configuration(manifest: &Table, documents: &[Document]) -> Value {
    JsonObject::new(
        FactIdentity {
            key: "configuration:pyproject",
            path: "pyproject.toml",
        }
        .base(),
    )
    .merged(json!({
        "assignments": configuration_assignments(documents),
        "python_target": python_target(manifest),
    }))
}
