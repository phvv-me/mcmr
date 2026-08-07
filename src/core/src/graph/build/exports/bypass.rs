use super::facade::{Package, outside_facade};
use crate::graph::contracts::{EdgeKind, Export, ExportBypass, Reference};
use std::collections::{BTreeMap, BTreeSet};

/// Where one export's symbol is declared, read from the target path the export names.
#[derive(Clone, Copy)]
struct Origin<'a> {
    module: &'a str,
    package: Package<'a>,
}

impl<'a> Origin<'a> {
    /// Read the declaring module and its package out of one fully qualified target.
    fn of(target: &'a str) -> Self {
        let module = target.rsplit_once('.').map_or(target, |(module, _)| module);
        let package = module
            .rsplit_once('.')
            .map_or(module, |(package, _)| package);
        Self {
            module,
            package: Package(package),
        }
    }
}

/// Choose the shortest public route that reaches each exported target.
pub(super) fn preferred_routes(exports: &[Export]) -> BTreeMap<String, String> {
    let mut found = BTreeMap::new();
    for export in exports {
        let public_name = format!("{}.{}", export.module, export.name);
        let candidate = (public_name.split('.').count(), public_name);
        found
            .entry(export.target.clone())
            .and_modify(|current: &mut (usize, String)| {
                if candidate < *current {
                    *current = candidate.clone();
                }
            })
            .or_insert(candidate);
    }
    found
        .into_iter()
        .map(|(target, (_, route))| (target, route))
        .collect()
}

/// Record every reference that reaches one export's target without writing its public route.
pub(super) fn bypasses(
    export: &Export,
    references: &[&Reference],
    preferred: &BTreeMap<String, String>,
    reachability: &BTreeMap<String, BTreeSet<String>>,
) -> Vec<ExportBypass> {
    let public_name = format!("{}.{}", export.module, export.name);
    if preferred.get(&export.target) != Some(&public_name) {
        return Vec::new();
    }
    let origin = Origin::of(&export.target);
    references
        .iter()
        .filter(|reference| is_bypass(export, reference, &public_name, origin))
        .map(|reference| ExportBypass {
            path: reference.location.path.clone(),
            line: reference.location.line,
            expression: reference.expression.clone(),
            module_node: reference.location.module_node.clone(),
            replacement_module: replacement_module(reference, origin, &export.module),
            binding_count: reference.resolution.binding_count,
            is_cycle_safe: !reachability
                .get(&export.module)
                .is_some_and(|reachable| reachable.contains(&reference.module)),
        })
        .collect()
}

fn is_bypass(
    export: &Export,
    reference: &Reference,
    public_name: &str,
    origin: Origin<'_>,
) -> bool {
    reference.kind == EdgeKind::Import
        && outside_facade(export, reference)
        && !nested_facade_implementation(export, reference)
        && !origin.package.holds(&reference.module)
        && reference.expression != public_name
}

fn nested_facade_implementation(export: &Export, reference: &Reference) -> bool {
    let Some((distribution, _)) = export.module.split_once('.') else {
        return false;
    };
    let marker = format!("{distribution}/");
    export
        .path
        .find(&marker)
        .map(|offset| &export.path[..offset + marker.len()])
        .is_some_and(|root| reference.location.path.starts_with(root))
}

/// Collect which module each module imports, keeping only modules this repository declares.
pub(super) fn import_graph(
    references: &[Reference],
    modules: &BTreeSet<String>,
) -> BTreeMap<String, BTreeSet<String>> {
    let mut imports: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for reference in references
        .iter()
        .filter(|reference| reference.kind == EdgeKind::Import)
    {
        if let Some(target) = declaring_module(&reference.expression, modules) {
            imports
                .entry(reference.module.clone())
                .or_default()
                .insert(target.to_string());
        }
    }
    imports
}

fn declaring_module<'a>(expression: &'a str, modules: &BTreeSet<String>) -> Option<&'a str> {
    let mut candidate = expression;
    loop {
        if modules.contains(candidate) {
            return Some(candidate);
        }
        candidate = candidate.rsplit_once('.')?.0;
    }
}

/// Close the import graph over every exporting module so a cycle question is one lookup.
pub(super) fn reachable_modules(
    imports: &BTreeMap<String, BTreeSet<String>>,
    exports: &[Export],
) -> BTreeMap<String, BTreeSet<String>> {
    exports
        .iter()
        .map(|export| export.module.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .map(|module| {
            let reachable = reachable_from(imports, &module);
            (module, reachable)
        })
        .collect()
}

fn reachable_from(imports: &BTreeMap<String, BTreeSet<String>>, start: &str) -> BTreeSet<String> {
    let mut reachable = BTreeSet::new();
    let mut pending = vec![start.to_string()];
    while let Some(module) = pending.pop() {
        if reachable.insert(module.clone())
            && let Some(dependencies) = imports.get(&module)
        {
            pending.extend(dependencies.iter().cloned());
        }
    }
    reachable
}

fn replacement_module(
    reference: &Reference,
    origin: Origin<'_>,
    public_module: &str,
) -> Option<String> {
    reference.location.module_node.as_ref().and_then(|node| {
        if node.text == origin.module {
            return Some(public_module.to_string());
        }
        let owner = origin
            .module
            .strip_suffix(&node.text)
            .unwrap_or_default()
            .trim_end_matches('.');
        public_module
            .strip_prefix(owner)
            .map(|module| module.trim_start_matches('.').to_string())
    })
}
