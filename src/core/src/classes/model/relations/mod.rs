use std::collections::{BTreeMap, BTreeSet};

use super::contracts::{Declared, Identity, Stated};

/// Return the class one base name reaches, through this module's imports or its own body.
///
/// A top-level class of that name wins outright, since it is the module-level binding a base is
/// written against. An import wins over a nested class of that name, because a nested class is only
/// in scope inside the class holding it. A nested class resolves last, which is what lets a class
/// inherit the sibling declared beside it in the same container.
pub(in crate::classes) fn resolve(
    module: &Stated,
    base: &str,
    definitions: &BTreeMap<Identity, &Declared>,
    reexports: &BTreeMap<Identity, Identity>,
) -> Option<Identity> {
    let own = (module.module.clone(), base.to_string());
    let declared = definitions.get(&own);
    if declared.is_some_and(|class| !class.is_nested()) {
        return Some(own);
    }
    let imported = module.imported.iter().find(|(_, name)| name == base);
    let reached = imported
        .cloned()
        .and_then(|held| defining_identity(held, definitions, reexports));
    reached.or_else(|| declared.map(|_| own))
}

fn defining_identity(
    held: Identity,
    definitions: &BTreeMap<Identity, &Declared>,
    reexports: &BTreeMap<Identity, Identity>,
) -> Option<Identity> {
    let mut visited = BTreeSet::new();
    let mut current = &held;
    let resolved = loop {
        if definitions.contains_key(current) {
            break current;
        }
        if !visited.insert(current) {
            return None;
        }
        current = reexports.get(current)?;
    };
    Some(resolved.clone())
}

/// Return every class some module reaching it ever calls, which is where one gets built.
pub(in crate::classes) fn built(
    stated: &[Stated],
    definitions: &BTreeMap<Identity, &Declared>,
) -> BTreeSet<Identity> {
    let mut found = BTreeSet::new();
    for module in stated {
        let reached = module.imported.iter().cloned().chain(
            module
                .declared
                .iter()
                .map(|class| (module.module.clone(), class.name.clone())),
        );
        for held in reached {
            if module.usage.called.contains(&held.1) && definitions.contains_key(&held) {
                found.insert(held);
            }
        }
    }
    found
}

/// Return which ordinary modules import which names from each module, keyed by the module read.
pub(in crate::classes) fn coimports(stated: &[Stated]) -> BTreeMap<&str, Vec<(&str, Vec<&str>)>> {
    let mut found: BTreeMap<&str, Vec<(&str, Vec<&str>)>> = BTreeMap::new();
    for module in stated.iter().filter(|module| !module.shape.is_package) {
        let mut taken: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
        for (origin, name) in &module.imported {
            taken
                .entry(origin.as_str())
                .or_default()
                .push(name.as_str());
        }
        for (origin, names) in taken {
            if origin != module.module {
                found
                    .entry(origin)
                    .or_default()
                    .push((module.module.as_str(), names));
            }
        }
    }
    found
}

/// Return which ordinary modules import each top-level class, keyed by definition.
///
/// An import statement binds a module-level name, so a nested class of the same name is never what
/// the importing module reached and never collects importers of its own.
pub(in crate::classes) fn importers<'repository>(
    stated: &'repository [Stated],
    definitions: &BTreeMap<Identity, &Declared>,
) -> BTreeMap<Identity, BTreeSet<&'repository str>> {
    let mut found: BTreeMap<Identity, BTreeSet<&str>> = BTreeMap::new();
    for module in stated {
        if module.shape.is_package || module.shape.is_reexport_only {
            continue;
        }
        for held in &module.imported {
            let reachable = definitions
                .get(held)
                .is_some_and(|class| !class.is_nested());
            if held.0 == module.module || !reachable {
                continue;
            }
            found
                .entry(held.clone())
                .or_default()
                .insert(module.module.as_str());
        }
    }
    found
}
