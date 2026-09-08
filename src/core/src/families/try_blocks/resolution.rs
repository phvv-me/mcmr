use crate::walk::{blocks, children, qualified_name};
use ruff_python_ast::visitor::{self, Visitor};
use ruff_python_ast::{Expr, ExprContext, ModModule, Stmt};
use ruff_text_size::Ranged;
use serde_json::{Value, json};
use std::collections::BTreeMap;

/// Literal import and receiver bindings, with repeated or conditional bindings unresolved.
#[derive(Clone, Default)]
struct Bindings {
    imports: BTreeMap<String, (String, u32)>,
    receivers: BTreeMap<String, (String, u32)>,
    writes: BTreeMap<String, usize>,
}

impl<'a> Visitor<'a> for Bindings {
    fn visit_expr(&mut self, expression: &'a Expr) {
        if let Expr::Name(name) = expression
            && name.ctx != ExprContext::Load
        {
            *self.writes.entry(name.id.to_string()).or_default() += 1;
        }
        if let Expr::Attribute(item) = expression
            && item.ctx != ExprContext::Load
        {
            let name = qualified_name(&item.value);
            let head = name.split('.').next().unwrap_or_default();
            *self.writes.entry(head.to_string()).or_default() += 1;
        }
        visitor::walk_expr(self, expression);
    }

    fn visit_stmt(&mut self, statement: &'a Stmt) {
        match statement {
            Stmt::FunctionDef(item) => *self.writes.entry(item.name.to_string()).or_default() += 1,
            Stmt::ClassDef(item) => *self.writes.entry(item.name.to_string()).or_default() += 1,
            Stmt::Import(item) => {
                for alias in &item.names {
                    let name = alias.asname.as_ref().map_or_else(
                        || alias.name.split('.').next().unwrap_or_default(),
                        |name| name.as_str(),
                    );
                    *self.writes.entry(name.to_string()).or_default() += 1;
                }
            }
            Stmt::ImportFrom(item) => {
                for alias in &item.names {
                    let name = alias.asname.as_ref().unwrap_or(&alias.name);
                    *self.writes.entry(name.to_string()).or_default() += 1;
                }
            }
            Stmt::Try(item) => {
                for handler in &item.handlers {
                    let ruff_python_ast::ExceptHandler::ExceptHandler(held) = handler;
                    if let Some(name) = &held.name {
                        *self.writes.entry(name.to_string()).or_default() += 1;
                    }
                }
                visitor::walk_stmt(self, statement);
            }
            _ => visitor::walk_stmt(self, statement),
        }
    }
}

impl Bindings {
    fn scope(&self, body: &[Stmt], parameters: Option<&ruff_python_ast::Parameters>) -> Self {
        let mut held = Self {
            writes: BTreeMap::new(),
            ..self.clone()
        };
        held.visit_body(body);
        if let Some(parameters) = parameters {
            for parameter in parameters {
                *held.writes.entry(parameter.name().to_string()).or_default() += 1;
            }
        }
        held.imports
            .retain(|name, _| !held.writes.contains_key(name));
        held.receivers
            .retain(|name, _| !held.writes.contains_key(name));
        for statement in body {
            held.import(statement);
        }
        if let Some(parameters) = parameters {
            for parameter in parameters {
                if let Some(annotation) = parameter.annotation() {
                    held.receiver(parameter.name().as_str(), annotation);
                }
            }
        }
        for statement in body {
            match statement {
                Stmt::Assign(item) if item.targets.len() == 1 => {
                    if let (Expr::Name(name), Expr::Call(call)) =
                        (&item.targets[0], item.value.as_ref())
                    {
                        held.receiver(name.id.as_str(), &call.func);
                    }
                }
                Stmt::AnnAssign(item) => {
                    if let (Expr::Name(name), Some(Expr::Call(call))) =
                        (item.target.as_ref(), item.value.as_deref())
                    {
                        held.receiver(name.id.as_str(), &call.func);
                    }
                }
                _ => {}
            }
        }
        held
    }

    fn import(&mut self, statement: &Stmt) {
        let (module, aliases) = match statement {
            Stmt::Import(item) => (None, item.names.as_slice()),
            Stmt::ImportFrom(item) if item.level == 0 => {
                (item.module.as_ref(), item.names.as_slice())
            }
            _ => return,
        };
        for alias in aliases {
            let local = alias.asname.as_ref().map_or_else(
                || {
                    if module.is_some() {
                        alias.name.as_str()
                    } else {
                        alias.name.split('.').next().unwrap_or_default()
                    }
                },
                |name| name.as_str(),
            );
            if self.writes.get(local) == Some(&1) {
                let origin = module.map_or_else(
                    || {
                        if alias.asname.is_some() {
                            alias.name.to_string()
                        } else {
                            local.to_string()
                        }
                    },
                    |module| format!("{module}.{}", alias.name),
                );
                self.imports
                    .insert(local.to_string(), (origin, statement.range().end().into()));
            }
        }
    }

    fn imported(&self, expression: &Expr) -> String {
        if !matches!(expression, Expr::Name(_) | Expr::Attribute(_)) {
            return String::new();
        }
        let name = qualified_name(expression);
        let (head, tail) = name.split_once('.').unwrap_or((&name, ""));
        self.imports
            .get(head)
            .filter(|(_, at)| *at <= u32::from(expression.range().start()))
            .map_or_else(String::new, |(origin, _)| {
                if tail.is_empty() {
                    origin.clone()
                } else {
                    format!("{origin}.{tail}")
                }
            })
    }

    fn receiver(&mut self, name: &str, annotation: &Expr) {
        if self.writes.get(name) != Some(&1) {
            return;
        }
        let base = if let Expr::Subscript(item) = annotation {
            item.value.as_ref()
        } else {
            annotation
        };
        let resolved = self.imported(base);
        if !resolved.is_empty() {
            self.receivers.insert(
                name.to_string(),
                (resolved, annotation.range().end().into()),
            );
        }
    }

    fn call(&self, expression: &Expr) -> String {
        if let Expr::Attribute(item) = expression
            && let Some((receiver, at)) = self.receivers.get(&qualified_name(&item.value))
            && *at <= u32::from(expression.range().start())
        {
            return format!("{receiver}.{}", item.attr);
        }
        self.imported(expression)
    }
}

pub(super) fn resolved_regions(module: &ModModule) -> BTreeMap<u32, Value> {
    let mut regions = BTreeMap::new();
    let bindings = Bindings::default().scope(&module.body, None);
    collect(&module.body, &bindings, &mut regions);
    regions
}

fn collect(body: &[Stmt], bindings: &Bindings, regions: &mut BTreeMap<u32, Value>) {
    for statement in body {
        if let Stmt::FunctionDef(item) = statement {
            let scope = bindings.scope(&item.body, Some(&item.parameters));
            collect(&item.body, &scope, regions);
        } else if let Stmt::ClassDef(item) = statement {
            // Class members are not lexical imports inside methods.
            let scope = bindings.scope(&item.body, None);
            for member in &item.body {
                let parent = if matches!(member, Stmt::FunctionDef(_)) {
                    bindings
                } else {
                    &scope
                };
                collect(std::slice::from_ref(member), parent, regions);
            }
        } else {
            if let Stmt::Try(item) = statement {
                let single = sole_call(&item.body);
                regions.insert(u32::from(item.range.start()), json!({
                    "protected_call_qualified_name": single.map_or_else(String::new, |call| bindings.call(&call.func)),
                    "caught_imports": item.handlers.iter().map(|handler| {
                        let ruff_python_ast::ExceptHandler::ExceptHandler(held) = handler;
                        held.type_.as_deref().map_or_else(String::new, |caught| bindings.imported(caught))
                    }).collect::<Vec<_>>(),
                }));
            }
            for nested in blocks(statement) {
                collect(nested, bindings, regions);
            }
        }
    }
}

fn sole_call(body: &[Stmt]) -> Option<&ruff_python_ast::ExprCall> {
    let expression = match body {
        [Stmt::Assign(item)]
            if item
                .targets
                .iter()
                .all(|target| matches!(target, Expr::Name(_))) =>
        {
            item.value.as_ref()
        }
        [Stmt::AnnAssign(item)] if matches!(item.target.as_ref(), Expr::Name(_)) => {
            item.value.as_deref()?
        }
        [Stmt::Expr(item)] => item.value.as_ref(),
        _ => return None,
    };
    let Expr::Call(call) = expression else {
        return None;
    };
    let mut pending = children(expression);
    while let Some(child) = pending.pop() {
        if matches!(child, Expr::Call(_) | Expr::Await(_) | Expr::Lambda(_)) {
            return None;
        }
        pending.extend(children(child));
    }
    Some(call)
}
