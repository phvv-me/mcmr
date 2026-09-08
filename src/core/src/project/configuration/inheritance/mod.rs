use std::hash::{DefaultHasher, Hash};
use std::path::Path;

use serde_json::{Value, json};
use toml::Table;

use super::super::read_table;

/// Read configuration ancestors only for a local tool-only manifest, never their source tree.
pub(in crate::project) fn sources(
    root: &Path,
    local: &Table,
) -> Result<Vec<(String, Table)>, String> {
    let mut sources = vec![("pyproject.toml".to_string(), local.clone())];
    if local.contains_key("project") {
        return Ok(sources);
    }
    let root = root
        .canonicalize()
        .map_err(|failure| format!("configuration owner could not be resolved: {failure}"))?;
    for (depth, ancestor) in root.ancestors().skip(1).enumerate() {
        let Some(manifest) = read_table(&ancestor.join("pyproject.toml"))? else {
            continue;
        };
        let complete = manifest.contains_key("project");
        sources.push((
            format!("{}pyproject.toml", "../".repeat(depth + 1)),
            manifest,
        ));
        if complete {
            break;
        }
    }
    Ok(sources)
}

/// Include every consulted ancestor's configuration identity, without discovering parent code.
pub(crate) fn hash_inherited(root: &Path, fingerprint: &mut DefaultHasher) -> Result<(), String> {
    let Some(local) = read_table(&root.join("pyproject.toml"))? else {
        return Ok(());
    };
    for (path, manifest) in sources(root, &local)?.into_iter().skip(1) {
        path.hash(fingerprint);
        toml::Value::Table(manifest).to_string().hash(fingerprint);
    }
    Ok(())
}

/// Supply the enclosing Python declaration while preserving explicit local checker targets.
pub(in crate::project) fn python(sources: &[(String, Table)]) -> Table {
    let mut effective = sources[0].1.clone();
    if !effective.contains_key("project")
        && let Some(project) = sources.iter().find_map(|(_, table)| table.get("project"))
    {
        effective.insert("project".to_string(), project.clone());
    }
    effective
}

/// Pytest selects one configuration; a local table is not merged with an enclosing one.
pub(in crate::project) fn pytest(sources: &[(String, Table)]) -> Result<(&str, Table), String> {
    let (path, source) = sources
        .iter()
        .find(|(_, table)| tool(table, "pytest").is_some())
        .unwrap_or(&sources[0]);
    let mut effective = source.clone();
    if let Some(coverage) = sources
        .iter()
        .find_map(|(_, table)| tool(table, "coverage"))
    {
        effective
            .entry("tool")
            .or_insert_with(|| toml::Value::Table(Table::new()))
            .as_table_mut()
            .ok_or_else(|| format!("{path} must define tool as a TOML table"))?
            .insert("coverage".to_string(), coverage.clone());
    }
    Ok((path, effective))
}

/// Retain actual manifest paths and relevant settings, without copying unrelated project data.
pub(in crate::project) fn evidence(sources: &[(String, Table)]) -> Value {
    json!(
        sources
            .iter()
            .map(|(path, table)| json!({
                "signal": format!("configuration:{path}"),
                "source": path,
        "detail": json!({
            "requires-python": table.get("project").and_then(|project| project.get("requires-python")),
            "python-targets": super::python_target::python_target(table, false),
            "pytest": tool(table, "pytest"),
            "coverage": tool(table, "coverage"),
        }).to_string(),
                "confidence": 1.0,
            }))
            .collect::<Vec<_>>()
    )
}

fn tool<'table>(table: &'table Table, name: &str) -> Option<&'table toml::Value> {
    table.get("tool").and_then(|tool| tool.get(name))
}
