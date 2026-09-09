use crate::source::Source;
use crate::walk::{qualified_name, walk};
use ruff_python_ast::{Expr, ModModule, Number, Stmt};
use ruff_text_size::Ranged;
use serde_json::{Value, json};

/// Every enumeration one file declares, with the values its members state.
///
/// The two lists this family carries beside the declarations are `scopes` and `files`, and neither
/// is a question one file can answer. Where a reused enum belongs is decided by every module that
/// imports it, and whether a shared `enums` package holds one enum per module is a claim about the
/// package rather than about any file in it. Both need a repository pass the way `ExceptionFact`
/// has one, so this builder states the declarations and leaves the two lists to it.
pub fn enums(source: &Source, module: &ModModule) -> Value {
    let declared: Vec<Value> = walk(module)
        .into_iter()
        .filter_map(|statement| match statement {
            Stmt::ClassDef(item) => enum_analysis(source, item),
            _ => None,
        })
        .collect();
    json!({"enums": declared})
}

pub(crate) fn is_enum(bases: &[String]) -> bool {
    enum_kind(bases).is_some()
}

fn enum_analysis(source: &Source, item: &ruff_python_ast::StmtClassDef) -> Option<Value> {
    let bases: Vec<String> = item
        .arguments
        .as_ref()
        .map(|arguments| arguments.args.iter().map(qualified_name).collect())
        .unwrap_or_default();
    let kind = enum_kind(&bases)?;
    let overrides = item
        .body
        .iter()
        .any(|statement| binds(statement, "_generate_next_value_"));
    // An ignored class binding is not necessarily an enum member, even in StrEnum.
    let mut values = (!overrides
        && !item
            .body
            .iter()
            .any(|statement| binds(statement, "_ignore_")))
    .then(Vec::new);
    let members: Vec<Value> = item
        .body
        .iter()
        .filter_map(|member| enum_member(source, member, kind, &mut values))
        .collect();
    Some(json!({
        "name": item.name.to_string(),
        "kind": kind,
        "members": members,
        "overrides_generate_next_value": overrides,
    }))
}

fn binds(statement: &Stmt, name: &str) -> bool {
    match statement {
        Stmt::Assign(assignment) => assignment
            .targets
            .iter()
            .any(|target| matches!(target, Expr::Name(target) if target.id.as_str() == name)),
        Stmt::AnnAssign(assignment) => matches!(assignment.target.as_ref(), Expr::Name(target)
            if target.id.as_str() == name),
        Stmt::FunctionDef(function) => function.name.as_str() == name,
        _ => false,
    }
}

pub(super) fn enum_kind(bases: &[String]) -> Option<&'static str> {
    bases
        .iter()
        .find_map(|base| match base.rsplit('.').next().unwrap_or(base) {
            "StrEnum" => Some("str_enum"),
            "IntEnum" => Some("int_enum"),
            "IntFlag" => Some("int_flag"),
            "Flag" => Some("flag"),
            "Enum" => Some("enum"),
            _ => None,
        })
}

fn enum_member(
    source: &Source,
    member: &Stmt,
    kind: &str,
    values: &mut Option<Vec<i64>>,
) -> Option<Value> {
    let (target, expression) = match member {
        Stmt::Assign(assignment) if assignment.targets.len() == 1 => {
            (&assignment.targets[0], assignment.value.as_ref())
        }
        Stmt::AnnAssign(assignment) => (assignment.target.as_ref(), assignment.value.as_deref()?),
        Stmt::Expr(_) | Stmt::FunctionDef(_) | Stmt::Pass(_) => return None,
        _ => {
            // Bindings inside unsupported statements can change every later auto().
            *values = None;
            return None;
        }
    };
    let Expr::Name(target) = target else {
        *values = None;
        return None;
    };
    let name = target.id.to_string();
    if name.starts_with("__") || (name.starts_with('_') && name.ends_with('_')) {
        return None;
    }
    let automatic = if values.is_none() {
        Value::Null
    } else if kind == "str_enum" {
        json!(name.to_lowercase())
    } else {
        json!(next_integer(values.as_deref(), kind))
    };
    let actual = match expression {
        Expr::NumberLiteral(literal) => match &literal.value {
            Number::Int(value) => value.as_i64(),
            _ => None,
        },
        Expr::Call(call)
            if matches!(qualified_name(&call.func).as_str(), "auto" | "enum.auto")
                && call.arguments.is_empty() =>
        {
            automatic.as_i64()
        }
        _ => None,
    };
    if kind != "str_enum" {
        match (values.as_mut(), actual) {
            (Some(previous), Some(value)) => previous.push(value),
            _ => *values = None,
        }
    }
    Some(json!({
        "name": name,
        "explicit_value": match expression {
            Expr::StringLiteral(literal) => json!(literal.value.to_str()),
            Expr::NumberLiteral(literal) => match &literal.value {
                Number::Int(value) => value
                    .as_i64()
                    .map_or_else(|| json!(value.to_string()), |value| json!(value)),
                _ => json!(format!("{:?}", literal.value)),
            },
            _ => json!(""),
        },
        "standard_auto_value": automatic,
        "value_node": source.node("expression", expression.range()),
    }))
}

/// Simulate standard integer generation only while every preceding value is known.
fn next_integer(values: Option<&[i64]>, kind: &str) -> Option<i64> {
    let Some(&maximum) = values?.iter().max() else {
        return Some(1);
    };
    if matches!(kind, "flag" | "int_flag") {
        let maximum = u64::try_from(maximum).ok()?;
        1_u64
            .checked_shl(64 - maximum.leading_zeros())?
            .try_into()
            .ok()
    } else {
        maximum.checked_add(1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::discovery::Document;
    use ruff_python_parser::parse_module;

    fn members(body: &str, kind: &str) -> Vec<Value> {
        let document = Document {
            relative: "feature.py".to_string(),
            source: format!("from enum import {kind}, auto\nclass Feature({kind}):\n{body}"),
        };
        let parsed = parse_module(&document.source).expect("the fixture parses");
        enums(&Source::new(&document), parsed.syntax())["enums"][0]["members"]
            .as_array()
            .expect("the class has members")
            .clone()
    }

    #[test]
    fn first_flag_two_is_not_redundant_but_first_flag_one_is() {
        for kind in ["Flag", "IntFlag"] {
            for first in [1, 2] {
                let extracted = members(
                    &format!(
                        concat!(
                            "    \"\"\"Keep persisted feature bits.\"\"\"\n",
                            "    SPANS = {}\n",
                            "    DEVICE = auto()\n",
                            "    MARKERS = auto()\n",
                            "    ACTIVITY = auto()\n",
                        ),
                        first,
                    ),
                    kind,
                );
                assert_eq!(extracted[0]["standard_auto_value"], 1);
                assert_eq!(
                    extracted[0]["explicit_value"] == extracted[0]["standard_auto_value"],
                    first == 1,
                );
                for (index, member) in extracted.iter().enumerate().skip(1) {
                    assert_eq!(member["standard_auto_value"], first << index);
                }
            }
        }
    }

    #[test]
    fn numeric_auto_uses_values_not_class_body_positions() {
        let extracted = members(
            concat!(
                "    \"\"\"Documented numeric protocol.\"\"\"\n",
                "    FIRST = 200\n",
                "    def label(self): return str(self)\n",
                "    SECOND: int = 201\n",
                "    THIRD = auto()\n",
                "    ALIAS = 200\n",
                "    FOURTH = 203\n",
            ),
            "IntEnum",
        );
        assert_eq!(
            extracted
                .iter()
                .map(|member| member["standard_auto_value"].clone())
                .collect::<Vec<_>>(),
            vec![json!(1), json!(201), json!(202), json!(203), json!(203)],
        );
    }

    #[test]
    fn unknown_previous_value_cannot_authorize_an_integer_autofix() {
        let extracted = members("    FIRST = configured()\n    SECOND = 2\n", "Flag");
        assert!(extracted[1]["standard_auto_value"].is_null());
    }

    #[test]
    fn custom_generation_and_ignored_bindings_do_not_authorize_string_rewrites() {
        for body in [
            "    _ignore_ = 'READY'\n    READY = 'ready'\n",
            "    _generate_next_value_ = custom\n    READY = 'ready'\n",
            "    READY = 'ready'\n    _generate_next_value_ = custom\n",
            "    def _generate_next_value_(*args): return 'custom'\n    READY = 'ready'\n",
        ] {
            let extracted = members(body, "StrEnum");
            assert!(extracted[0]["standard_auto_value"].is_null());
        }
    }
}
