use std::io::ErrorKind;
use std::path::Path;

use crate::discovery::Inventory;
use serde_json::{Value, json};
use toml::Table;

mod assignment_scope;
mod automation;
mod command_line;
mod configuration;
mod fact_identity;

use automation::automation;
use configuration::inheritance;
pub(crate) use configuration::inheritance::hash_inherited;
#[cfg(test)]
use configuration::minor;
use configuration::{configuration, test_suite};

/// The facts a repository states about itself in its own configuration files.
///
/// A project declares its test runner, its supported language version, and the commands that
/// operate it in configuration rather than in source. Reading that configuration keeps those rules
/// on the same evidence contract as every other rule instead of asking a project to restate what
/// it already wrote down.
pub fn facts(
    root: &Path,
    families: &[String],
    inventory: &Inventory,
) -> Result<Vec<(String, Value)>, String> {
    let manifest = read_table(&root.join("pyproject.toml"))?;
    let tooling = read_table(&root.join("mainboard.toml"))?;
    let mut built = Vec::new();
    let wants = |name: &str| families.iter().any(|family| family == name);
    if let Some(stated) = &manifest {
        let sources = inheritance::sources(root, stated)?;
        if wants("TestSuiteFact") {
            let (path, effective) = inheritance::pytest(&sources)?;
            let mut fact = test_suite(&effective);
            fact["evidence"] = inheritance::evidence(&sources);
            fact["evidence"].as_array_mut().expect("configuration evidence is a list").push(json!({
                "signal": "pytest-selection",
                "source": path,
                "detail": "Effective pytest options are selected from this manifest; local tool-only configuration remains the diagnostic and repair anchor.",
                "confidence": 1.0,
            }));
            built.push(("TestSuiteFact".to_string(), fact));
        }
        if wants("ProjectConfigurationFact") {
            let mut fact = configuration(
                &inheritance::python(&sources),
                &inventory.documents,
                !stated.contains_key("project"),
            );
            fact["evidence"] = inheritance::evidence(&sources);
            built.push(("ProjectConfigurationFact".to_string(), fact));
        }
    }
    if let Some(stated) = &tooling
        && wants("AutomationTaskFact")
    {
        built.push((
            "AutomationTaskFact".to_string(),
            automation(stated, &inventory.guides),
        ));
    }
    Ok(built)
}

/// Read an owned manifest when it exists and distinguish absence from invalid evidence.
fn read_table(path: &Path) -> Result<Option<Table>, String> {
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(failure) if failure.kind() == ErrorKind::NotFound => return Ok(None),
        Err(failure) => {
            return Err(format!("{} could not be read: {failure}", path.display()));
        }
    };
    text.parse::<Table>()
        .map(Some)
        .map_err(|failure| format!("{} is not valid TOML: {failure}", path.display()))
}

#[cfg(test)]
mod tests;
