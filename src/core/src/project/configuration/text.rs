use toml::Table;

/// Read one TOML key as text, treating an absent or non-text value as nothing written.
pub(super) fn text_of(table: &Table, name: &str) -> String {
    table
        .get(name)
        .and_then(toml::Value::as_str)
        .unwrap_or_default()
        .to_string()
}
