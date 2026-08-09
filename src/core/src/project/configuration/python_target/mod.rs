use serde_json::{Value, json};
use toml::Table;

use super::text::text_of;

/// State which Python version a project claims and which version each of its tools is set to.
pub(super) fn python_target(manifest: &Table) -> Value {
    let requires = manifest
        .get("project")
        .and_then(toml::Value::as_table)
        .map(|table| text_of(table, "requires-python"))
        .unwrap_or_default();
    json!({
        "project_minimum_minor": minor(&requires),
        "configured_tools": versioned_tools(manifest),
        "tool_target_minors": target_minors(manifest),
        "per_file_target_minors": per_file_target_minors(manifest),
    })
}

/// Return the minor version one declaration accepts, however that version is written.
pub(in crate::project) fn minor(declaration: &str) -> Option<u32> {
    let specifier = declaration
        .split(',')
        .find(|part| part.contains(">="))
        .unwrap_or(declaration);
    let digits: String = specifier
        .chars()
        .filter(|letter| letter.is_ascii_digit() || *letter == '.')
        .collect();
    match digits.split_once('.') {
        Some((_, minor)) => minor.parse().ok(),
        None => digits
            .strip_prefix('3')
            .and_then(|minor| minor.parse().ok()),
    }
}

/// Every configured tool that states a Python target, whichever key it states it under.
fn versioned_tools(manifest: &Table) -> Vec<String> {
    manifest
        .get("tool")
        .and_then(toml::Value::as_table)
        .map(|table| {
            table
                .iter()
                .filter(|(_, settings)| target_key(settings).is_some())
                .map(|(name, _)| name.clone())
                .collect()
        })
        .unwrap_or_default()
}

fn target_key(settings: &toml::Value) -> Option<&str> {
    ["target-version", "python_version", "python-version"]
        .iter()
        .find_map(|key| settings.get(key).and_then(toml::Value::as_str))
}

fn target_minors(manifest: &Table) -> Value {
    let tools = manifest.get("tool").and_then(toml::Value::as_table);
    let mut targets = serde_json::Map::new();
    for (name, table) in tools.into_iter().flatten() {
        if let Some(value) = target_key(table).and_then(minor) {
            targets.insert(name.clone(), json!(value));
        }
    }
    Value::Object(targets)
}

/// Return every Python minor Ruff assigns to an individual source pattern.
fn per_file_target_minors(manifest: &Table) -> Vec<u32> {
    manifest
        .get("tool")
        .and_then(|tool| tool.get("ruff"))
        .and_then(|ruff| ruff.get("per-file-target-version"))
        .and_then(toml::Value::as_table)
        .into_iter()
        .flat_map(Table::values)
        .filter_map(toml::Value::as_str)
        .filter_map(minor)
        .collect()
}
