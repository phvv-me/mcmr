use ruff_python_ast::{Expr, Stmt};
use ruff_text_size::Ranged;

mod documentation;
mod expressions;
mod fields;
mod reexport;
mod traversal;

pub use documentation::docstring;
pub use expressions::{children, expression_tree, expressions};
pub use fields::{annotation_name, class_instance_fields};
pub use reexport::is_reexport_only;
pub use traversal::{blocks, statements, walk};

pub fn qualified_name(expression: &Expr) -> String {
    match expression {
        Expr::Name(name) => name.id.to_string(),
        Expr::Attribute(attribute) => {
            let base = qualified_name(&attribute.value);
            if base.is_empty() {
                String::new()
            } else {
                format!("{base}.{}", attribute.attr)
            }
        }
        Expr::Call(call) => qualified_name(&call.func),
        _ => String::new(),
    }
}

/// Return the range one statement block covers, from its first statement to its last.
pub fn body_range(body: &[Stmt]) -> ruff_text_size::TextRange {
    match (body.first(), body.last()) {
        (Some(first), Some(last)) => {
            ruff_text_size::TextRange::new(first.range().start(), last.range().end())
        }
        _ => ruff_text_size::TextRange::default(),
    }
}

pub fn declared_name(statement: &Stmt) -> Option<String> {
    match statement {
        Stmt::ClassDef(item) => Some(item.name.to_string()),
        Stmt::FunctionDef(item) => Some(item.name.to_string()),
        _ => None,
    }
}
