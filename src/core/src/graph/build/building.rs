use super::exports::{References, enrich};
use super::reachable::Reachable;
use crate::graph::contracts::{Edge, EdgeKind, Export, Graph, Language, Node, Reference, Stated};
use crate::graph::resolution_engine::{ResolutionContext, resolve};
use std::collections::{BTreeMap, BTreeSet};

/// The repository graph while the frontend and resolution passes are still filling it.
pub(super) struct Building {
    nodes: BTreeMap<String, Node>,
    edges: Vec<Edge>,
    references: Vec<Reference>,
    export_references: Vec<Reference>,
    aliases: BTreeMap<String, BTreeMap<String, String>>,
    exports: Vec<Export>,
}

impl Building {
    /// Start from the workspace nodes and edges that exist before any file is read.
    pub(super) fn new(nodes: BTreeMap<String, Node>, edges: Vec<Edge>) -> Self {
        Self {
            nodes,
            edges,
            references: Vec::new(),
            export_references: Vec::new(),
            aliases: BTreeMap::new(),
            exports: Vec::new(),
        }
    }

    /// Absorb everything one file stated about itself, in the order the documents were read.
    pub(super) fn absorb(&mut self, path: &str, module: String, mut stated: Stated) {
        self.exports.extend(stated.exports.iter().map(|name| {
            Export {
                module: module.clone(),
                name: name.clone(),
                target: stated
                    .aliases
                    .get(name)
                    .cloned()
                    .unwrap_or_else(|| format!("{module}.{name}")),
                path: path.to_string(),
                nodes: stated.export_nodes.get(name).cloned().unwrap_or_default(),
                consumer_count: 0,
                bypasses: Vec::new(),
            }
        }));
        self.merge(std::mem::take(&mut stated.nodes));
        self.aliases.insert(module, stated.aliases);
        self.edges.append(&mut stated.edges);
        self.references.append(&mut stated.references);
        self.export_references.append(&mut stated.export_references);
    }

    /// Count who consumes each export and record every route that goes around it.
    pub(super) fn enrich_exports(&mut self, modules: &BTreeSet<String>) {
        enrich(
            &mut self.exports,
            References {
                runtime: &self.references,
                type_checking: &self.export_references,
            },
            modules,
        );
    }

    /// Hand over the finished repository graph.
    pub(super) fn finish(self) -> Graph {
        Graph {
            nodes: self.nodes.into_values().collect(),
            edges: self.edges,
            exports: self.exports,
        }
    }

    /// Read the names every stated reference is allowed to land on.
    pub(super) fn reachable(&self) -> Reachable {
        Reachable::of(&self.nodes)
    }

    /// Attach every stated reference to the declaration it named.
    pub(super) fn resolve(&mut self, reachable: &Reachable) {
        let lookup = crate::native::Lookup::of(&reachable.symbols);
        for reference in &self.references {
            let symbols = match reference.kind {
                EdgeKind::Import => &reachable.modules,
                _ => &reachable.symbols,
            };
            attach(
                reference,
                reachable,
                &lookup,
                ResolutionContext {
                    symbols,
                    aliases: &self.aliases,
                    nodes: &mut self.nodes,
                    edges: &mut self.edges,
                },
            );
        }
    }

    /// Keep every node once, narrowing the visibility when two files declare the same one.
    fn merge(&mut self, nodes: Vec<Node>) {
        for node in nodes {
            let (id, visibility) = (node.id.clone(), node.visibility);
            self.nodes
                .entry(id)
                .and_modify(|held| held.visibility = held.visibility.narrower(visibility))
                .or_insert(node);
        }
    }
}

/// Attach one reference through the resolver its language owns.
fn attach(
    reference: &Reference,
    reachable: &Reachable,
    lookup: &crate::native::Lookup,
    context: ResolutionContext<'_>,
) {
    match reference.language {
        Language::Rust => crate::rust::resolve(reference, context),
        Language::C | Language::Cpp | Language::Cuda => {
            crate::native::resolve(
                reference,
                context.symbols,
                lookup,
                context.nodes,
                context.edges,
            );
        }
        Language::TypeScript => crate::typescript::resolve(
            reference,
            crate::typescript::ResolutionContext {
                modules: &reachable.modules,
                symbols: &reachable.symbols,
                aliases: context.aliases,
                nodes: context.nodes,
                edges: context.edges,
            },
        ),
        _ => resolve(reference, context),
    }
}
