use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use tokenizers::Tokenizer;

#[pyclass(frozen)]
pub struct HuggingFaceTokenizer {
    tokenizer: Tokenizer,
}

#[pymethods]
impl HuggingFaceTokenizer {
    #[new]
    fn new(path: &str) -> PyResult<Self> {
        Ok(Self {
            tokenizer: Tokenizer::from_file(path)
                .map_err(|error| PyRuntimeError::new_err(error.to_string()))?,
        })
    }

    fn count(&self, text: &str) -> PyResult<usize> {
        self.tokenizer
            .encode(text, false)
            .map(|encoding| encoding.len())
            .map_err(|error| PyRuntimeError::new_err(error.to_string()))
    }
}
