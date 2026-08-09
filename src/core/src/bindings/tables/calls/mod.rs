use crate::bindings::frames::evidence::EvidenceView;
use crate::bindings::frames::located::{boolean_fact_frame, fact_key, located_fact};
use crate::bindings::frames::string_values::{StringValueColumns, selected_string_value_frame};
use crate::bindings::frames::{combined_frame, evidence_relation, frame_result};
use crate::bindings::relations::NestedRow;
use crate::calls::{CallRecord, CallSite, EvidenceRecord};
use expressions::expression_frames;
use frames::CallFrames;
use polars::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

mod expressions;
mod frames;
mod rows;
mod support;

use rows::call_rows;
use support::CallSupportFrames;

located_fact!(CallRecord);

impl EvidenceView for EvidenceRecord {
    fn signal(&self) -> &str {
        &self.signal
    }

    fn detail(&self) -> &str {
        &self.detail
    }

    fn source(&self) -> &str {
        &self.source
    }

    fn confidence(&self) -> f64 {
        self.confidence
    }
}

/// The call frames Python may take, exactly once.
///
/// Every frame moves across the boundary in one hand-off rather than through a frame at a time,
/// because a getter that quietly empties what it returns cannot say whether a second reader is
/// looking at real rows or at what the first reader left behind.
#[pyclass]
pub(in crate::bindings) struct CallTables {
    frames: Option<CallFrames>,
}

#[pymethods]
impl CallTables {
    fn frames<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
        self.frames
            .take()
            .ok_or_else(|| PyRuntimeError::new_err("the call tables were already read"))?
            .into_dict(py)
    }
}

impl CallTables {
    pub(in crate::bindings) fn build(records: &[CallRecord]) -> Result<Self, String> {
        let (expressions, expression_ancestry, mapping_entries) =
            frame_result(expression_frames(records))?;
        Ok(Self {
            frames: Some(CallFrames {
                support: CallSupportFrames {
                    facts: frame_result(call_fact_frame(records))?,
                    evidence: frame_result(evidence_frame(records))?,
                },
                calls: frame_result(call_frame(records))?,
                keywords: frame_result(keyword_frame(records))?,
                expressions,
                expression_ancestry,
                mapping_entries,
                module_bindings: frame_result(module_binding_frame(records))?,
            }),
        })
    }
}

fn call_fact_frame(records: &[CallRecord]) -> PolarsResult<DataFrame> {
    boolean_fact_frame(records, "is_test", |record| record.is_test)
}

fn call_frame(records: &[CallRecord]) -> PolarsResult<DataFrame> {
    let rows = call_rows(records);
    combined_frame(
        rows.len(),
        [
            call_identity_frame(&rows)?,
            call_flag_frame(&rows)?,
            call_node_frame(&rows)?,
            callee_node_frame(&rows)?,
        ],
    )
}

fn call_identity_frame(rows: &[NestedRow<'_, CallSite>]) -> PolarsResult<DataFrame> {
    df![
        "call_id" => rows.iter().map(|row| row.id.clone()).collect::<Vec<_>>(),
        "fact_id" => rows.iter().map(|row| row.fact_id).collect::<Vec<_>>(),
        "ordinal" => rows.iter().map(|row| row.ordinal).collect::<Vec<_>>(),
        "qualified_name" => rows.iter().map(|row| row.call().target.qualified_name.clone()).collect::<Vec<_>>(),
        "target_id" => rows.iter().map(|row| row.call().target.target_id.clone()).collect::<Vec<_>>(),
        "path" => rows.iter().map(|row| row.call().syntax.path.clone()).collect::<Vec<_>>(),
        "assigned_target" => rows.iter().map(|row| row.call().syntax.assigned_target.clone()).collect::<Vec<_>>(),
    ]
}

fn call_flag_frame(rows: &[NestedRow<'_, CallSite>]) -> PolarsResult<DataFrame> {
    df![
        "result_is_discarded" => rows.iter().map(|row| row.call().context.result_is_discarded).collect::<Vec<_>>(),
        "is_external" => rows.iter().map(|row| row.call().target.is_external).collect::<Vec<_>>(),
        "is_standard_library" => rows.iter().map(|row| row.call().target.is_standard_library).collect::<Vec<_>>(),
        "is_first_party" => rows.iter().map(|row| row.call().target.is_first_party).collect::<Vec<_>>(),
        "is_constructor" => rows.iter().map(|row| row.call().target.is_constructor).collect::<Vec<_>>(),
        "is_shadowed" => rows.iter().map(|row| row.call().context.is_shadowed).collect::<Vec<_>>(),
        "has_ambiguous_alias" => rows.iter().map(|row| row.call().context.has_ambiguous_alias).collect::<Vec<_>>(),
        "is_decorator_factory" => rows.iter().map(|row| row.call().context.is_decorator_factory).collect::<Vec<_>>(),
        "has_starred_arguments" => rows.iter().map(|row| row.call().context.has_starred_arguments).collect::<Vec<_>>(),
        "enclosing_is_async" => rows.iter().map(|row| row.call().context.enclosing_is_async).collect::<Vec<_>>(),
    ]
}

fn call_node_frame(rows: &[NestedRow<'_, CallSite>]) -> PolarsResult<DataFrame> {
    df![
        "node_id" => rows.iter().map(|row| row.call().syntax.node.id.clone()).collect::<Vec<_>>(),
        "node_path" => rows.iter().map(|row| row.call().syntax.node.span.path.clone()).collect::<Vec<_>>(),
        "node_start_line" => rows.iter().map(|row| row.call().syntax.node.span.start_line as u64).collect::<Vec<_>>(),
        "node_start_column" => rows.iter().map(|row| row.call().syntax.node.span.start_column as u64).collect::<Vec<_>>(),
        "node_end_line" => rows.iter().map(|row| row.call().syntax.node.span.end_line as u64).collect::<Vec<_>>(),
        "node_end_column" => rows.iter().map(|row| row.call().syntax.node.span.end_column as u64).collect::<Vec<_>>(),
        "node_kind" => rows.iter().map(|row| row.call().syntax.node.kind.clone()).collect::<Vec<_>>(),
        "node_text" => rows.iter().map(|row| row.call().syntax.node.text.clone()).collect::<Vec<_>>(),
    ]
}

fn callee_node_frame(rows: &[NestedRow<'_, CallSite>]) -> PolarsResult<DataFrame> {
    df![
        "callee_id" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.id.clone())).collect::<Vec<_>>(),
        "callee_path" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.span.path.clone())).collect::<Vec<_>>(),
        "callee_start_line" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.span.start_line as u64)).collect::<Vec<_>>(),
        "callee_start_column" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.span.start_column as u64)).collect::<Vec<_>>(),
        "callee_end_line" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.span.end_line as u64)).collect::<Vec<_>>(),
        "callee_end_column" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.span.end_column as u64)).collect::<Vec<_>>(),
        "callee_kind" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.kind.clone())).collect::<Vec<_>>(),
        "callee_text" => rows.iter().map(|row| row.call().syntax.callee.as_ref().map(|node| node.text.clone())).collect::<Vec<_>>(),
    ]
}

fn keyword_frame(records: &[CallRecord]) -> PolarsResult<DataFrame> {
    selected_string_value_frame(
        StringValueColumns {
            id: "call_id",
            value: "name",
        },
        call_rows(records)
            .into_iter()
            .map(|row| (row.id, row.value)),
        |call| &call.syntax.keyword_names,
    )
}

fn module_binding_frame(records: &[CallRecord]) -> PolarsResult<DataFrame> {
    let rows = records
        .iter()
        .flat_map(|record| {
            record
                .module_bindings
                .iter()
                .enumerate()
                .map(move |(ordinal, name)| (record.key.as_str(), ordinal as u64, name.as_str()))
        })
        .collect::<Vec<_>>();
    df![
        "fact_id" => rows.iter().map(|row| row.0).collect::<Vec<_>>(),
        "ordinal" => rows.iter().map(|row| row.1).collect::<Vec<_>>(),
        "name" => rows.iter().map(|row| row.2).collect::<Vec<_>>(),
    ]
}

fn evidence_frame(records: &[CallRecord]) -> PolarsResult<DataFrame> {
    evidence_relation(records, "fact_id", fact_key, |record| &record.evidence)
}
