use crate::protocol::JsonObject;
use serde_json::{Value, json};
use toml::Table;

use super::super::command_line::CommandLine;
use super::super::fact_identity::FactIdentity;
use super::text::text_of;

/// State how strictly a repository runs its own test suite, from what pytest is configured with.
pub(in crate::project) fn test_suite(manifest: &Table) -> Value {
    let pytest = manifest
        .get("tool")
        .and_then(|tool| tool.get("pytest"))
        .and_then(|pytest| pytest.get("ini_options"))
        .and_then(toml::Value::as_table);
    let options = pytest
        .map(|table| text_of(table, "addopts"))
        .unwrap_or_default();
    let command = CommandLine::new(&options);
    let coverage = command.has_flag("--cov");
    let strict = command.has_flag("--strict")
        || pytest
            .and_then(|table| table.get("strict"))
            .and_then(toml::Value::as_bool)
            .unwrap_or(false);
    let strict_control = |name: &str, switch: &str| {
        pytest
            .and_then(|table| table.get(name))
            .and_then(toml::Value::as_bool)
            .unwrap_or_else(|| strict || (!switch.is_empty() && command.has_flag(switch)))
    };
    JsonObject::new(
        FactIdentity {
            key: "suite:pytest",
            path: "pyproject.toml",
        }
        .base(),
    )
    .merged(json!({
        "strict_controls": {
            "strict_config": strict_control("strict_config", "--strict-config"),
            "strict_markers": strict_control("strict_markers", "--strict-markers"),
            "strict_parametrization_ids": strict_control("strict_parametrization_ids", ""),
            "strict_xfail": strict_control("strict_xfail", ""),
        },
        "import_mode": command.option("--import-mode")
            .or_else(|| pytest.map(|table| text_of(table, "import_mode")))
            .filter(|mode| !mode.is_empty())
            .unwrap_or_else(|| "prepend".to_string()),
        "anyio_mode": pytest.map(|table| text_of(table, "anyio_mode")).unwrap_or_default(),
        "asyncio_mode": pytest
            .map(|table| text_of(table, "asyncio_mode"))
            .unwrap_or_default(),
        "is_coverage_configured": coverage,
        "is_branch_coverage_enabled": branch_coverage(manifest),
    }))
}

fn branch_coverage(manifest: &Table) -> bool {
    manifest
        .get("tool")
        .and_then(|tool| tool.get("coverage"))
        .and_then(|coverage| coverage.get("run"))
        .and_then(|run| run.get("branch"))
        .and_then(toml::Value::as_bool)
        .unwrap_or(false)
}
