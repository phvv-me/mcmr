use serde_json::{Value, json};
use toml::Table;

use super::text::text_of;

/// State which Python version a project claims and which version each of its tools is set to.
pub(super) fn python_target(manifest: &Table, inherited: bool) -> Value {
    let requires = manifest
        .get("project")
        .and_then(toml::Value::as_table)
        .map(|table| text_of(table, "requires-python"))
        .unwrap_or_default();
    let minimum = minor(&requires);
    json!({
        "project_minimum_minor": minimum,
        "configured_tools": versioned_tools(manifest),
        "tool_target_minors": target_minors(manifest, inherited.then_some(minimum).flatten()),
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
                .filter(|(name, settings)| configured(name, settings))
                .map(|(name, _)| name.clone())
                .collect()
        })
        .unwrap_or_default()
}

fn configured(name: &str, settings: &toml::Value) -> bool {
    ["ruff", "pyrefly", "ty", "mypy", "pyright", "basedpyright"].contains(&name)
        || target_value(settings).is_some()
}

fn target_value(settings: &toml::Value) -> Option<&toml::Value> {
    [
        "target-version",
        "python_version",
        "python-version",
        "pythonVersion",
    ]
    .iter()
    .find_map(|key| settings.get(key))
    .or_else(|| {
        settings
            .get("environment")
            .and_then(|environment| environment.get("python-version"))
    })
}

fn target_minors(manifest: &Table, inherited: Option<u32>) -> Value {
    let tools = manifest.get("tool").and_then(toml::Value::as_table);
    let mut targets = serde_json::Map::new();
    for (name, table) in tools.into_iter().flatten() {
        let target = match target_value(table) {
            Some(value) => value.as_str().and_then(minor),
            None if configured(name, table) => inherited,
            None => None,
        };
        if let Some(value) = target {
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
