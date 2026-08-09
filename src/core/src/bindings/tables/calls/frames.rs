use super::support::CallSupportFrames;
use polars::prelude::DataFrame;
use pyo3::prelude::*;
use pyo3_polars::PyDataFrame;

/// Every frame one call analysis produced, under the names the Python table binder reads.
pub(super) struct CallFrames {
    pub(super) support: CallSupportFrames,
    pub(super) calls: DataFrame,
    pub(super) keywords: DataFrame,
    pub(super) expressions: DataFrame,
    pub(super) expression_ancestry: DataFrame,
    pub(super) mapping_entries: DataFrame,
    pub(super) module_bindings: DataFrame,
}

impl CallFrames {
    /// Hand every frame to Python at once, by value, so nothing can be read a second time.
    pub(super) fn into_dict(self, py: Python<'_>) -> PyResult<Bound<'_, pyo3::types::PyDict>> {
        let frames = pyo3::types::PyDict::new(py);
        for (name, frame) in [
            ("facts", self.support.facts),
            ("calls", self.calls),
            ("keywords", self.keywords),
            ("expressions", self.expressions),
            ("expression_ancestry", self.expression_ancestry),
            ("mapping_entries", self.mapping_entries),
            ("module_bindings", self.module_bindings),
            ("evidence", self.support.evidence),
        ] {
            frames.set_item(name, PyDataFrame(frame))?;
        }
        Ok(frames)
    }
}
