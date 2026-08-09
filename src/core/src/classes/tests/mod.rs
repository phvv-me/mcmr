use super::*;

mod inheritance;
mod models;

fn enriched(sources: &[(&str, &str)]) -> Vec<Value> {
    let mut facts = extracted(sources);
    facts
        .remove("ClassFact")
        .unwrap_or_default()
        .into_iter()
        .flat_map(|fact| {
            fact["classes"]
                .as_array()
                .cloned()
                .unwrap_or_default()
                .into_iter()
        })
        .collect()
}

fn extracted(sources: &[(&str, &str)]) -> BTreeMap<String, Vec<Value>> {
    let documents: Vec<Document> = sources
        .iter()
        .map(|(relative, source)| Document {
            relative: (*relative).to_string(),
            source: (*source).to_string(),
        })
        .collect();
    let packages = Packages::of(&documents);
    let mut facts: BTreeMap<String, Vec<Value>> = BTreeMap::from([
        ("ClassFact".to_string(), Vec::new()),
        ("FunctionFact".to_string(), Vec::new()),
    ]);
    let mut stats = crate::protocol::Stats::default();
    for document in &documents {
        crate::python::extract(document, &packages, &mut facts, &mut stats);
    }
    enrich(&mut facts, &documents, &packages);
    facts
}

fn class(classes: &[Value], name: impl AsRef<str>) -> &Value {
    classes
        .iter()
        .find(|held| held["name"] == name.as_ref())
        .expect("the class is declared")
}
