use crate::graph::contracts::{Export, Reference};
use bypass::{bypasses, import_graph, preferred_routes, reachable_modules};
use facade::consumes_route;
use std::collections::{BTreeMap, BTreeSet};

mod bypass;
mod facade;

/// Every reference the frontends stated, split by whether it exists while the program runs.
///
/// A type-checking import consumes an export as much as a runtime one does, so both sets answer
/// the consumer question, while only the runtime set may close an import cycle.
pub(super) struct References<'a> {
    pub(super) runtime: &'a [Reference],
    pub(super) type_checking: &'a [Reference],
}

/// Count who consumes each export and record every route that reaches its target around it.
pub(super) fn enrich(
    exports: &mut [Export],
    references: References<'_>,
    modules: &BTreeSet<String>,
) {
    let routes = routes_by_public_name(exports);
    let mut consumers: Vec<BTreeSet<&str>> = vec![BTreeSet::new(); exports.len()];
    for reference in references.runtime.iter().chain(references.type_checking) {
        record_consumer(exports, reference, &routes, &mut consumers);
    }
    for (export, consumers) in exports.iter_mut().zip(consumers) {
        export.consumer_count = consumers.len();
    }
    let preferred = preferred_routes(exports);
    let reachability = reachable_modules(&import_graph(references.runtime, modules), exports);
    let indexed = references_by_expression(references.runtime);
    for export in exports {
        export.bypasses = bypasses(
            export,
            indexed
                .get(export.target.as_str())
                .map_or(&[], Vec::as_slice),
            &preferred,
            &reachability,
        );
    }
}

/// Credit one reference to every export whose public route it names from outside that facade.
fn record_consumer<'a>(
    exports: &[Export],
    reference: &'a Reference,
    routes: &BTreeMap<String, Vec<usize>>,
    consumers: &mut [BTreeSet<&'a str>],
) {
    for route in expression_routes(&reference.expression) {
        for index in routes.get(route).into_iter().flatten() {
            if consumes_route(&exports[*index], reference) {
                consumers[*index].insert(reference.location.path.as_str());
            }
        }
    }
}

fn routes_by_public_name(exports: &[Export]) -> BTreeMap<String, Vec<usize>> {
    let mut routes: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for (index, export) in exports.iter().enumerate() {
        routes
            .entry(format!("{}.{}", export.module, export.name))
            .or_default()
            .push(index);
    }
    routes
}

fn expression_routes(expression: &str) -> impl Iterator<Item = &str> {
    expression
        .match_indices('.')
        .map(|(index, _)| &expression[..index])
        .chain(std::iter::once(expression))
}

fn references_by_expression(references: &[Reference]) -> BTreeMap<&str, Vec<&Reference>> {
    let mut indexed: BTreeMap<&str, Vec<&Reference>> = BTreeMap::new();
    for reference in references {
        indexed
            .entry(reference.expression.as_str())
            .or_default()
            .push(reference);
    }
    indexed
}
