use super::documentation::docstring;
use ruff_python_ast::{Expr, ModModule, Stmt};

/// Whether one module hands names on rather than declaring anything of its own.
///
/// A module holding nothing but imports is a seam, so importing through it does not prove that a
/// second place depends on the name. Its own consumers do, and they are counted where they are. A
/// leading docstring states nothing the module owns, so it is read past before the rest is judged.
pub fn is_reexport_only(module: &ModModule) -> bool {
    let body = match module.body.split_first() {
        Some((first, rest)) if docstring(std::slice::from_ref(first)).is_some() => rest,
        _ => module.body.as_slice(),
    };
    body.iter().all(hands_name_on)
}

/// Whether one statement passes a name through rather than declaring one.
fn hands_name_on(statement: &Stmt) -> bool {
    match statement {
        Stmt::Import(_) | Stmt::ImportFrom(_) => true,
        Stmt::Assign(item) => item
            .targets
            .iter()
            .all(|target| matches!(target, Expr::Name(name) if name.id.as_str() == "__all__")),
        _ => false,
    }
}
