use super::element::Element;
use super::located::Located;
use crate::lexical::CorpusFile;
use std::collections::BTreeSet;
use typst_syntax::ast::{self, AstNode, Expr};
use typst_syntax::{Source, SyntaxKind, SyntaxNode};

/// Read literal Typst documents through the language's own syntax tree, without evaluating code.
pub struct TypstReader<'a> {
    path: &'a str,
    source: &'a Source,
    elements: Vec<Located>,
    pending_math: bool,
    bindings: BTreeSet<String>,
}

impl TypstReader<'_> {
    pub fn read(file: &CorpusFile) -> Result<Vec<Located>, String> {
        let source = Source::detached(file.text.clone());
        if source.root().diagnosis().errors {
            return Err(format!(
                "{}: Typst syntax errors prevent manuscript analysis",
                file.path
            ));
        }
        let mut reader = TypstReader {
            path: &file.path,
            source: &source,
            elements: vec![Located::new(Element::BodyStart, &file.path, 1)],
            pending_math: false,
            bindings: BTreeSet::new(),
        };
        let markup = source
            .root()
            .cast::<ast::Markup>()
            .ok_or("missing Typst markup root")?;
        reader.markup(markup)?;
        reader.close_math(1);
        Ok(reader.elements)
    }

    fn markup(&mut self, markup: ast::Markup<'_>) -> Result<(), String> {
        for expression in markup.exprs() {
            self.expression(expression)?;
        }
        Ok(())
    }

    fn expression(&mut self, expression: Expr<'_>) -> Result<(), String> {
        let offset = self
            .source
            .find(expression.span())
            .map_or(0, |node| node.offset());
        let line = self.source.lines().byte_to_line(offset).unwrap_or(0) + 1;
        if !matches!(expression, Expr::Space(_) | Expr::Label(_)) {
            self.close_math(line);
        }
        match expression {
            Expr::Text(text) => self.push(Element::Text(text.get().to_string()), line),
            Expr::Space(_) => self.push(Element::Text(" ".to_string()), line),
            Expr::Parbreak(_) | Expr::Linebreak(_) => self.push(Element::ParagraphBreak, line),
            Expr::Escape(escape) => self.push(Element::Text(escape.get().to_string()), line),
            Expr::Shorthand(short) => self.push(Element::Text(short.get().to_string()), line),
            Expr::SmartQuote(quote) => self.push(
                Element::Text(if quote.double() { "\"" } else { "'" }.to_string()),
                line,
            ),
            Expr::Heading(heading) => {
                if has_runtime(heading.body().to_untyped()) {
                    return self.unresolved(expression, line);
                }
                let title: String = heading
                    .body()
                    .exprs()
                    .filter(|part| !matches!(part, Expr::Label(_)))
                    .map(|part| part.to_untyped().full_text().to_string())
                    .collect();
                self.push(
                    Element::Section {
                        level: u8::try_from(heading.depth().get()).unwrap_or(u8::MAX),
                        title: title.trim().to_string(),
                    },
                    line,
                );
                for part in heading
                    .body()
                    .exprs()
                    .filter(|part| matches!(part, Expr::Label(_) | Expr::Ref(_)))
                {
                    self.expression(part)?;
                }
            }
            Expr::Label(label) => {
                self.push(Element::Label(label.get().to_string()), line);
                self.close_math(line);
            }
            Expr::Ref(reference) => self.push(
                Element::Reference {
                    target: reference.target().to_string(),
                    command: "@".to_string(),
                },
                line,
            ),
            Expr::Equation(equation) => {
                if has_runtime(equation.body().to_untyped()) {
                    return self.unresolved(expression, line);
                }
                if equation.block() {
                    self.push(Element::EnvironmentOpen("equation".to_string()), line);
                    self.pending_math = true;
                } else {
                    self.push(Element::Text(" · ".to_string()), line);
                }
                self.push(
                    Element::Math {
                        text: equation.body().to_untyped().full_text().to_string(),
                        display: equation.block(),
                    },
                    line,
                );
            }
            Expr::Strong(strong) => self.markup(strong.body())?,
            Expr::Emph(emphasis) => self.markup(emphasis.body())?,
            Expr::ContentBlock(block) => self.markup(block.body())?,
            Expr::ListItem(item) => self.item(item.body(), line)?,
            Expr::EnumItem(item) => self.item(item.body(), line)?,
            Expr::TermItem(item) => {
                self.push(Element::ParagraphBreak, line);
                self.push(
                    Element::ItemLabel(item.term().to_untyped().full_text().to_string()),
                    line,
                );
                self.markup(item.description())?;
            }
            Expr::ModuleInclude(include) => {
                let Expr::Str(path) = include.source() else {
                    return self.unresolved(expression, line);
                };
                self.push(Element::Include(path.get().to_string()), line);
            }
            Expr::FuncCall(call) => self.transparent_call(call, line)?,
            Expr::LetBinding(binding) => self.bindings.extend(
                binding
                    .kind()
                    .bindings()
                    .iter()
                    .map(|name| name.get().to_string()),
            ),
            Expr::Raw(_) | Expr::SetRule(_) => {}
            _ => return self.unresolved(expression, line),
        }
        Ok(())
    }

    /// Only layout wrappers with literal content are transparent; arbitrary calls need evaluation.
    fn transparent_call(&mut self, call: ast::FuncCall<'_>, line: usize) -> Result<(), String> {
        let name = call.callee().to_untyped().full_text();
        if self.bindings.contains(name.as_str())
            || !["text", "strong", "emph", "block", "box", "align", "columns"]
                .contains(&name.as_str())
        {
            return self.unresolved(Expr::FuncCall(call), line);
        }
        for argument in call.args().items() {
            match argument {
                ast::Arg::Pos(Expr::ContentBlock(body)) => self.markup(body.body())?,
                ast::Arg::Named(named) if named.name().get() == "body" => {
                    let Expr::ContentBlock(body) = named.expr() else {
                        return self.unresolved(Expr::FuncCall(call), line);
                    };
                    self.markup(body.body())?;
                }
                ast::Arg::Named(_) => {}
                _ => return self.unresolved(Expr::FuncCall(call), line),
            }
        }
        Ok(())
    }

    fn item(&mut self, body: ast::Markup<'_>, line: usize) -> Result<(), String> {
        self.push(Element::ParagraphBreak, line);
        self.markup(body)
    }

    fn unresolved(&self, expression: Expr<'_>, line: usize) -> Result<(), String> {
        Err(format!(
            "{}:{line}: unresolved Typst {}: runtime-generated content is outside the literal manuscript frontend",
            self.path,
            expression.to_untyped().kind().name()
        ))
    }

    fn close_math(&mut self, line: usize) {
        if self.pending_math {
            self.push(Element::EnvironmentClose("equation".to_string()), line);
            self.pending_math = false;
        }
    }

    fn push(&mut self, element: Element, line: usize) {
        self.elements.push(Located::new(element, self.path, line));
    }
}

/// Keep Typst identifiers and their mathematical styling intact; never apply TeX tokenization.
pub fn named(math: &str) -> Vec<String> {
    let root = typst_syntax::parse_math(math);
    let mut found = Vec::new();
    symbols(&root, &mut found);
    found
}

fn symbols(node: &SyntaxNode, found: &mut Vec<String>) {
    match node.kind() {
        SyntaxKind::MathIdent | SyntaxKind::MathText => {
            let name = node.leaf_text();
            if name.chars().all(char::is_alphabetic) && super::symbols::is_quantity(name) {
                found.push(name.to_string());
            }
        }
        SyntaxKind::MathAttach => {
            let attached = node
                .cast::<ast::MathAttach>()
                .expect("the syntax kind is an attachment");
            let mut base = Vec::new();
            symbols(attached.base().to_untyped(), &mut base);
            if base.len() == 1 {
                let suffix = attached.bottom().map_or(String::new(), |bottom| {
                    format!("_{}", bottom.to_untyped().full_text())
                });
                found.push(format!("{}{suffix}", base[0]));
            } else {
                found.extend(base);
            }
        }
        SyntaxKind::MathCall => {
            let call = node
                .cast::<ast::MathCall>()
                .expect("the syntax kind is a math call");
            let name = call.callee().to_untyped().full_text();
            if ["bb", "cal", "frak", "bold", "hat", "tilde", "arrow"].contains(&name.as_str()) {
                found.push(node.full_text().split_whitespace().collect());
            } else {
                if super::symbols::is_quantity(&name)
                    && !["mat", "cases", "lr", "op"].contains(&name.as_str())
                {
                    found.push(name.to_string());
                }
                for argument in call.args().arg_items() {
                    symbols(argument.arg.to_untyped(), found);
                }
            }
        }
        SyntaxKind::Str | SyntaxKind::CodeBlock => {}
        _ => {
            for child in node.children() {
                symbols(child, found);
            }
        }
    }
}

fn has_runtime(node: &SyntaxNode) -> bool {
    matches!(
        node.kind(),
        SyntaxKind::Ident
            | SyntaxKind::FuncCall
            | SyntaxKind::CodeBlock
            | SyntaxKind::Contextual
            | SyntaxKind::Conditional
    ) || node.children().any(has_runtime)
}
