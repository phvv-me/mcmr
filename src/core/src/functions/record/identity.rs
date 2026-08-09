use crate::calls::EvidenceRecord;
use crate::protocol::Span;
use crate::source::is_test_path;
use serde::Serialize;

/// What one callable is called and where it is written, which together name its fact.
///
/// The fact identity is derived here from the span and the name, and nothing outside can restate
/// either one afterwards, so the identity a rule cites can never drift from the callable it names.
#[derive(Clone, Debug, Serialize)]
pub struct FunctionIdentity {
    key: String,
    span: Span,
    language: String,
    is_test: bool,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    evidence: Vec<EvidenceRecord>,
    name: String,
    scope: String,
}

impl FunctionIdentity {
    /// Name one callable, deriving the fact identity from where it sits and what it is called.
    pub fn of(span: Span, language: &str, name: String) -> Self {
        Self {
            key: format!(
                "function:{}:{}:{}:{name}",
                span.path, span.start_line, span.start_column
            ),
            is_test: is_test_path(&span.path),
            span,
            language: language.to_string(),
            evidence: Vec::new(),
            name,
            scope: String::new(),
        }
    }

    pub fn evidence(&self) -> &[EvidenceRecord] {
        &self.evidence
    }

    pub fn is_test(&self) -> bool {
        self.is_test
    }

    pub fn key(&self) -> &str {
        &self.key
    }

    pub fn language(&self) -> &str {
        &self.language
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn scope(&self) -> &str {
        &self.scope
    }

    pub fn span(&self) -> &Span {
        &self.span
    }

    /// State which scope holds this callable, which its frontend settles after parsing the body.
    pub fn state_scope(&mut self, scope: &str) {
        self.scope = scope.to_string();
    }
}

impl Default for FunctionIdentity {
    fn default() -> Self {
        Self::of(Span::default(), "", String::new())
    }
}
