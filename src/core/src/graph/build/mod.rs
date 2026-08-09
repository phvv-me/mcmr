use super::construction::workspace;
use super::contracts::{Graph, Language, Stated};
use super::naming::Naming;
use super::python::python;
use crate::discovery::Document;
use crate::source::Source;
use building::Building;
use rayon::prelude::*;

mod building;
mod exports;
mod reachable;

/// Build the whole repository graph from documents that were already read.
///
/// One naming pass decides what every file calls itself, one frontend pass per language states the
/// definitions and the references each file makes, and one resolution pass attaches every reference
/// to the declaration it named. A language reaches the graph by adding a frontend to the middle
/// pass, which is why the ends of this function say nothing about any particular language.
pub fn build(root: &str, documents: &[Document]) -> Result<Graph, String> {
    let naming = Naming::of(root, documents);
    let specifiers = crate::typescript::Specifiers::of(root, naming.typescript(documents))?;
    let (nodes, edges) = workspace(root, documents, &naming);
    let mut building = Building::new(nodes, edges);
    for (index, module, stated) in state(documents, &naming, &specifiers) {
        building.absorb(&documents[index].relative, module, stated);
    }
    Ok(building.resolve())
}

/// State every document through the frontend its language owns, back in document order.
fn state(
    documents: &[Document],
    naming: &Naming,
    specifiers: &crate::typescript::Specifiers,
) -> Vec<(usize, String, Stated)> {
    let mut frontends: Vec<(usize, String, Stated)> = documents
        .par_iter()
        .enumerate()
        .filter_map(|(index, document)| {
            let (language, module) = naming.module(&document.relative)?;
            let source = Source::new(document);
            let stated = match language {
                Language::Python => python(source, &module),
                Language::Rust => crate::rust::graph(source, &module),
                Language::TypeScript => crate::typescript::graph(source, &module, specifiers),
                native => crate::native::graph(source, &module, native),
            }?;
            Some((index, module, stated))
        })
        .collect();
    frontends.sort_by_key(|(index, _, _)| *index);
    frontends
}
