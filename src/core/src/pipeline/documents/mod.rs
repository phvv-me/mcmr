use super::super::deferred::DeferredFacts;
use super::super::delivery::Delivery;
use super::super::runtime::{FACT_BATCH_SIZE, TypedRows};
use crate::extraction::DocumentExtraction;
use crate::protocol::Stats;
use std::sync::mpsc::sync_channel;

mod extracted;
mod selection;

use extracted::ExtractedDocument;
use selection::ExtractionSelection;

/// Extract documents on every available worker while delivering results in source order.
pub(super) fn extract_documents<Emit>(
    extraction: DocumentExtraction<'_>,
    deferred: &mut DeferredFacts,
    delivery: &mut Delivery<Emit>,
    stats: &mut Stats,
    mut typed: TypedRows<'_>,
) -> Result<(), String>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    let documents = extraction.documents;
    let packages = extraction.packages;
    let per_file = extraction.families;
    let workers = rayon::current_num_threads().min(documents.len()).max(1);
    let selected = ExtractionSelection::of(&typed);
    std::thread::scope(|scope| {
        let receivers = (0..workers)
            .map(|offset| {
                let (send, receive) = sync_channel(1);
                scope.spawn(move || {
                    for document in documents.iter().skip(offset).step_by(workers) {
                        if send
                            .send(ExtractedDocument::of(
                                document, packages, per_file, selected,
                            ))
                            .is_err()
                        {
                            return;
                        }
                    }
                });
                receive
            })
            .collect::<Vec<_>>();
        for index in 0..documents.len() {
            let extracted = receivers[index % workers]
                .recv()
                .map_err(|_| "a kernel extraction worker stopped before its document")??;
            let (extracted_facts, rows, document_stats) = extracted.into_parts();
            stats.parse_failure_count += document_stats.parse_failure_count;
            if let Some(output) = typed.families.functions.as_deref_mut() {
                output.extend(rows.functions);
            }
            if let Some(output) = typed.families.calls.as_deref_mut() {
                output.extend(rows.calls);
            }
            if let Some(output) = typed.families.classes.as_deref_mut() {
                if !selected.retention.classes && output.is_empty() && !rows.classes.is_empty() {
                    delivery.mark_typed("ClassFact", FACT_BATCH_SIZE)?;
                }
                output.extend(rows.classes);
            }
            if let Some(output) = typed.families.import_bindings.as_deref_mut() {
                if output.is_empty() && !rows.import_bindings.is_empty() {
                    delivery.mark_typed("ImportBindingFact", FACT_BATCH_SIZE)?;
                }
                output.extend(rows.import_bindings);
            }
            if let Some(output) = typed.families.syntax.as_deref_mut() {
                if output.is_empty() && !rows.syntax.is_empty() {
                    delivery.mark_typed("SyntaxFact", FACT_BATCH_SIZE)?;
                }
                output.extend(rows.syntax);
            }
            if let Some(output) = typed.families.attribute_accesses.as_deref_mut() {
                if output.is_empty() && !rows.attribute_accesses.is_empty() {
                    delivery.mark_typed("AttributeAccessFact", FACT_BATCH_SIZE)?;
                }
                output.extend(rows.attribute_accesses);
            }
            if let Some(output) = typed.families.string_expressions.as_deref_mut() {
                if output.is_empty() && !rows.string_expressions.is_empty() {
                    delivery.mark_typed("StringExpressionFact", FACT_BATCH_SIZE)?;
                }
                output.extend(rows.string_expressions);
            }
            for (family, facts) in extracted_facts {
                if deferred.holds(&family) {
                    deferred.write(&family, facts)?;
                } else {
                    delivery.send(family, facts)?;
                }
            }
        }
        Ok(())
    })
}
