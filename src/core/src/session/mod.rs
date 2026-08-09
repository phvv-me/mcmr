use super::deferred::DeferredMode;
use super::delivery::{CaptureSelection, Delivery, GenericCapture};
use super::pipeline::analyze;
use super::runtime::{TypedFamilies, TypedRows};
use crate::protocol::{Request, Response, Stats, VERSION};
use std::collections::BTreeSet;

mod contracts;

pub use contracts::{SessionFamilies, SessionOutput};

/// Answer one analysis request, which is everything the binary does.
pub fn run(request: &Request) -> Result<Response, String> {
    let built = built_families(request);
    let mut discard = |_: String, _: Vec<serde_json::Value>| Ok(());
    let mut delivery = Delivery::new(&built, GenericCapture::default(), &mut discard);
    let (graph, stats) = analyze(
        request,
        &built,
        &mut delivery,
        TypedRows::default(),
        DeferredMode::Spools,
    )?;
    Ok(Response {
        version: VERSION,
        facts: delivery.close(&request.families)?.retained,
        graph,
        stats,
    })
}

/// Answer one fact request incrementally, completing each repository-wide phase before the next.
pub fn run_stream<Emit>(request: &Request, mut emit: Emit) -> Result<Stats, String>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    if request.graph {
        return Err(
            "a repository graph is one document and cannot use the fact stream".to_string(),
        );
    }
    let built = built_families(request);
    let mut delivery = Delivery::new(&[], GenericCapture::default(), &mut emit);
    let (_, stats) = analyze(
        request,
        &built,
        &mut delivery,
        TypedRows::default(),
        DeferredMode::Spools,
    )?;
    delivery.close(&request.families)?;
    Ok(stats)
}

/// Build selected typed rows while streaming every unmigrated family from the same analysis.
pub fn run_session<Emit>(
    request: &Request,
    typed_families: &[String],
    emit: Emit,
) -> Result<SessionOutput, String>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    run_session_with_generic(
        request,
        SessionFamilies {
            typed: typed_families,
            generic: &[],
        },
        emit,
    )
}

/// Build typed rows and optional generic mirrors from one repository analysis.
pub fn run_session_with_generic<Emit>(
    request: &Request,
    families: SessionFamilies<'_>,
    mut emit: Emit,
) -> Result<SessionOutput, String>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    if request.graph {
        return Err(
            "a repository graph is one document and cannot use the analysis session".to_string(),
        );
    }
    let generic_families = families.generic.iter().cloned().collect::<BTreeSet<_>>();
    let selected_request = selected_request(request, &generic_families);
    let built = built_families(&selected_request);
    let capture = GenericCapture::new(CaptureSelection {
        selected: generic_families,
        mirrored: request.families.iter().cloned().collect(),
    });
    let mut delivery = Delivery::new(&[], capture, &mut emit);
    let mut output = SessionOutput::default();
    let (_, stats) = analyze(
        &selected_request,
        &built,
        &mut delivery,
        typed_rows(&mut output, families),
        DeferredMode::Memory,
    )?;
    Ok(SessionOutput {
        generic: delivery.close(&request.families)?.generic,
        stats,
        ..output
    })
}

fn selected_request(request: &Request, generic: &BTreeSet<String>) -> Request {
    let mut families = request.families.clone();
    families.extend(generic.iter().cloned());
    families.sort();
    families.dedup();
    Request {
        root: request.root.clone(),
        families,
        suffixes: request.suffixes.clone(),
        graph: request.graph,
        stream: request.stream,
        fingerprint_only: request.fingerprint_only,
        python_standard_library: request.python_standard_library.clone(),
    }
}

fn typed_rows<'a>(output: &'a mut SessionOutput, families: SessionFamilies<'_>) -> TypedRows<'a> {
    let selected = |family: &str| families.typed.iter().any(|wanted| wanted == family);
    TypedRows {
        families: TypedFamilies {
            functions: selected("FunctionFact").then_some(&mut output.facts.functions),
            calls: selected("CallFact").then_some(&mut output.facts.calls),
            classes: selected("ClassFact").then_some(&mut output.facts.classes),
            import_bindings: selected("ImportBindingFact")
                .then_some(&mut output.facts.import_bindings),
            syntax: selected("SyntaxFact").then_some(&mut output.facts.syntax),
            attribute_accesses: selected("AttributeAccessFact")
                .then_some(&mut output.facts.attribute_accesses),
            string_expressions: selected("StringExpressionFact")
                .then_some(&mut output.facts.string_expressions),
        },
        ..TypedRows::default()
    }
}

fn built_families(request: &Request) -> Vec<String> {
    request.families.clone()
}
