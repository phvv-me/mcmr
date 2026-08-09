use ruff_python_ast::{Expr, Stmt};

/// Return the prose one body opens with, as a summary line and the dedented rest.
pub fn docstring(body: &[Stmt]) -> Option<String> {
    match body.first() {
        Some(Stmt::Expr(item)) => match item.value.as_ref() {
            Expr::StringLiteral(literal) => {
                let raw = literal.value.to_str();
                let (summary, body) = raw.split_once('\n').unwrap_or((raw, ""));
                let body = textwrap::dedent(body);
                let body = body.trim_matches('\n');
                Some(match body.is_empty() {
                    true => summary.trim().to_string(),
                    false => format!("{}\n\n{body}", summary.trim()),
                })
            }
            _ => None,
        },
        _ => None,
    }
}
