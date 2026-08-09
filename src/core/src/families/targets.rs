use ruff_python_ast::{Expr, Stmt};

/// Return the expressions one statement writes to rather than reads from.
///
/// An assignment and a `with` binding are the two ways a statement names something without that
/// name appearing among the expressions it evaluates, so any pass counting how often a name is
/// bound has to read these beside what the statement holds.
pub(super) fn declared_targets(statement: &Stmt) -> Vec<&Expr> {
    match statement {
        Stmt::Assign(item) => item.targets.iter().collect(),
        Stmt::AnnAssign(item) => vec![item.target.as_ref()],
        Stmt::AugAssign(item) => vec![item.target.as_ref()],
        Stmt::With(item) => item
            .items
            .iter()
            .filter_map(|entry| entry.optional_vars.as_deref())
            .collect(),
        _ => Vec::new(),
    }
}
