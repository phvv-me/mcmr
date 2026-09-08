use super::command::Command;
use super::cursor::Cursor;
use super::delimiter::{BRACE, BRACKET};
use super::element::Element;
use super::located::Located;
use super::role::Role;
use crate::lexical::CorpusFile;
use std::collections::BTreeMap;

/// Environments whose opening takes mandatory arguments, and how many they take.
///
/// A column specification is layout rather than prose, so reading it as running text would put
/// `@{}p{4.6cm}` in the middle of a sentence and make every measurement of that sentence wrong.
const ARGUED: &[(&str, usize)] = &[
    ("array", 1),
    ("longtable", 1),
    ("minipage", 1),
    ("tabular", 1),
    ("tabularx", 2),
    ("tabulary", 2),
];

/// Read one LaTeX file into the markup-neutral element stream.
///
/// TeX is macro expansion rather than a grammar, so nothing here pretends to parse it. What a
/// reader of the printed document sees is a sequence of headings, statements, labels, references,
/// mathematics and prose, and every one of those is spelled by a control sequence this scanner
/// recognizes. A name it does not recognize is a word boundary, which is the honest answer for a
/// macro whose expansion only the TeX engine knows.
pub struct LatexReader {
    path: String,
    elements: Vec<Located>,
    text: String,
    text_line: usize,
    plain_style: bool,
    theorem_styles: BTreeMap<String, bool>,
}

impl LatexReader {
    /// Read one file's elements in the order the file states them.
    pub fn read(file: &CorpusFile) -> Vec<Located> {
        let mut reader = Self {
            path: file.path.clone(),
            elements: Vec::new(),
            text: String::new(),
            text_line: 1,
            plain_style: true,
            theorem_styles: BTreeMap::from([("plain".to_string(), true)]),
        };
        let mut cursor = Cursor::new(&file.text);
        while !cursor.done() {
            reader.step(&mut cursor);
        }
        reader.flush();
        reader.elements
    }

    /// Consume the arguments an environment opening takes, keeping the references they carry.
    ///
    /// An optional argument is a title or a placement hint and a mandatory one is layout, so
    /// neither is prose the reader reads in the flow. Both are still scanned, because a statement
    /// title routinely carries the citation that says where the statement came from.
    fn arguments(&mut self, kind: &str, cursor: &mut Cursor<'_>, line: usize) {
        let mut consumed = Vec::new();
        while let Some(optional) = BRACKET.read(cursor) {
            consumed.push(optional);
        }
        let mandatory = ARGUED
            .iter()
            .find(|(name, _)| *name == kind.trim_end_matches('*'))
            .map_or(0, |(_, count)| *count);
        for _ in 0..mandatory {
            consumed.extend(BRACE.read(cursor));
        }
        for body in consumed {
            self.nested(&body, line);
        }
    }

    /// Emit the caption of the float this sits inside, keeping it out of the running prose.
    fn caption(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        drop(BRACKET.read(cursor));
        self.grouped(cursor, line, Element::Caption);
    }

    /// Emit one citation per key, carrying the locator the last bracket pins it to.
    fn citation(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        let first = BRACKET.read(cursor);
        let pin = BRACKET.read(cursor).or(first).unwrap_or_default();
        let Some(keys) = BRACE.read(cursor) else {
            return;
        };
        for key in keys.split(',') {
            self.push(
                Element::Citation {
                    key: key.trim().to_string(),
                    pin: pin.trim().to_string(),
                },
                line,
            );
        }
        self.text.push_str(" \u{b7} ");
    }

    /// Close one environment, ending whatever prose run was open inside it.
    fn close_environment(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        self.grouped(cursor, line, Element::EnvironmentClose);
    }

    /// Read one control sequence and whatever arguments its behaviour claims.
    fn control(&mut self, cursor: &mut Cursor<'_>) {
        let line = cursor.line();
        cursor.bump();
        let name =
            cursor.take_while(|character| character.is_ascii_alphabetic() || character == '@');
        if name.is_empty() {
            self.escape(cursor, line);
            return;
        }
        cursor.eat("*");
        self.dispatch(&name, cursor, line);
    }

    /// Apply one named command, which either emits an element or opens a math span.
    fn dispatch(&mut self, name: &str, cursor: &mut Cursor<'_>, line: usize) {
        match Command::of(name) {
            Command::EnvironmentOpen => self.open_environment(cursor, line),
            Command::EnvironmentClose => self.close_environment(cursor, line),
            Command::Section(level) => self.heading(level, cursor, line),
            Command::Label => self.grouped(cursor, line, Element::Label),
            Command::Reference => self.reference(name, cursor, line),
            Command::Citation => self.citation(cursor, line),
            Command::Include => self.grouped(cursor, line, Element::Include),
            Command::Caption => self.caption(cursor, line),
            Command::StatementKind => self.statement_kind(cursor, line),
            Command::StatementStyle => self.statement_style(cursor),
            Command::Macro => self.macro_name(name, cursor, line),
            Command::EnvironmentKind => self.environment_kind(cursor),
            Command::TheoremStyleKind => self.theorem_style_kind(cursor),
            Command::ParagraphBreak => self.push(Element::ParagraphBreak, line),
            Command::Item => {
                self.push(Element::ParagraphBreak, line);
                if let Some(label) = BRACKET.read(cursor) {
                    self.push(Element::ItemLabel(label), line);
                }
            }
            Command::BibliographyItem => {
                self.push(Element::ParagraphBreak, line);
                drop(BRACKET.read(cursor));
                drop(BRACE.read(cursor));
            }
            Command::Emphasis => self.emphasis(name, cursor, line),
            Command::Discarded => self.discarded(name, cursor),
            Command::Plain => {
                self.push(Element::MacroUse(name.to_string()), line);
                self.text.push(' ');
            }
        }
    }

    /// Consume layout and metadata arguments while leaving any actual text body to the reader.
    fn discarded(&mut self, name: &str, cursor: &mut Cursor<'_>) {
        while BRACKET.read(cursor).is_some() {}
        let count = match name {
            "addcontentsline" | "definecolor" => 3,
            "addtolength" | "setcounter" | "setlength" | "pdfbookmark" => 2,
            _ => 1,
        };
        for _ in 0..count {
            drop(BRACE.read(cursor));
        }
    }

    /// Emit one math span set on its own, which ends the prose run around it.
    fn display_math(&mut self, body: String, line: usize) {
        let punctuation = Self::terminal_punctuation(&body);
        self.push(
            Element::Math {
                text: body,
                display: true,
            },
            line,
        );
        self.text.push_str(" · ");
        if let Some(punctuation) = punctuation {
            self.text.push(punctuation);
            self.text.push(' ');
        }
    }

    /// Keep rendered terminal punctuation, not formula tokens or environment/label metadata.
    fn terminal_punctuation(body: &str) -> Option<char> {
        let mut cursor = Cursor::new(body);
        let mut terminal = None;
        while let Some(character) = cursor.bump() {
            match character {
                '%' => drop(cursor.take_until("\n")),
                '\\' => {
                    let name = cursor.take_while(|character| character.is_ascii_alphabetic());
                    match name.as_str() {
                        "end" | "label" | "tag" => drop(BRACE.read(&mut cursor)),
                        "quad" | "qquad" | "notag" | "nonumber" => {}
                        "right" | "left" if cursor.eat(".") => {}
                        "" => {
                            cursor.bump();
                        }
                        _ => terminal = None,
                    }
                }
                '}' => {}
                character if character.is_whitespace() => {}
                character => terminal = ".!?;,:".contains(character).then_some(character),
            }
        }
        terminal
    }

    /// Read one dollar-delimited math span, inline or display.
    fn dollar(&mut self, cursor: &mut Cursor<'_>) {
        let line = cursor.line();
        cursor.bump();
        let display = cursor.eat("$");
        let terminator = if display { "$$" } else { "$" };
        let body = cursor.take_until(terminator);
        if display {
            self.display_math(body, line);
        } else {
            self.inline_math(body, line);
        }
    }

    /// Emit marked text without consuming it, so it counts as prose as well as a marking.
    fn emphasis(&mut self, command: &str, cursor: &mut Cursor<'_>, line: usize) {
        let mut peeked = cursor.clone();
        if let Some(marked) = BRACE.read(&mut peeked) {
            self.push(
                Element::Emphasis {
                    command: command.to_string(),
                    marked: marked.trim().to_string(),
                },
                line,
            );
        }
    }

    /// Read a control sequence whose name is one punctuation character.
    ///
    /// The two that matter open mathematics. Every other escape stands for the character it
    /// escapes, so it joins the running text and cannot end a sentence the way a bare dot would.
    fn escape(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        match cursor.bump() {
            Some('[') => self.display_math(cursor.take_until("\\]"), line),
            Some('(') => self.inline_math(cursor.take_until("\\)"), line),
            Some('\\') => self.row_break(line),
            Some(character) => self.text.push(character),
            None => {}
        }
    }

    /// Emit whatever running text has accumulated, and start a new run.
    fn flush(&mut self) {
        let text = std::mem::take(&mut self.text);
        if !text.trim().is_empty() {
            self.elements.push(Located::new(
                Element::Text(text),
                &self.path,
                self.text_line,
            ));
        }
    }

    /// Emit one element built from a single consumed group.
    fn grouped(
        &mut self,
        cursor: &mut Cursor<'_>,
        line: usize,
        build: impl Fn(String) -> Element,
    ) {
        if let Some(argument) = BRACE.read(cursor) {
            self.push(build(argument.trim().to_string()), line);
        }
    }

    /// Emit one heading and the level it sits at.
    fn heading(&mut self, level: u8, cursor: &mut Cursor<'_>, line: usize) {
        drop(BRACKET.read(cursor));
        let Some(title) = BRACE.read(cursor) else {
            return;
        };
        self.push(
            Element::Section {
                level,
                title: title.trim().to_string(),
            },
            line,
        );
    }

    /// Emit one math span set inside a sentence, standing a placeholder in for it.
    fn inline_math(&mut self, body: String, line: usize) {
        self.text.push_str(" \u{b7} ");
        self.push(
            Element::Math {
                text: body,
                display: false,
            },
            line,
        );
    }

    /// Emit the cross reference targets declared inside a body taken whole.
    fn labels_inside(&mut self, body: &str, line: usize) {
        for tail in body.split("\\label").skip(1) {
            let mut cursor = Cursor::new(tail);
            if let Some(name) = BRACE.read(&mut cursor) {
                self.push(Element::Label(name.trim().to_string()), line);
            }
        }
    }

    /// Emit the name of a macro this document declares.
    fn macro_name(&mut self, command: &str, cursor: &mut Cursor<'_>, line: usize) {
        drop(cursor.take_while(char::is_whitespace));
        let declared = BRACE.read(cursor).unwrap_or_else(|| {
            cursor.eat("\\");
            cursor.take_while(|character| character.is_ascii_alphabetic() || character == '@')
        });
        let name = declared.trim().trim_start_matches('\\').to_string();
        drop(cursor.take_while(char::is_whitespace));
        let mut has_arguments = false;
        while BRACKET.read(cursor).is_some() {
            has_arguments = true;
            drop(cursor.take_while(char::is_whitespace));
        }
        let body = BRACE.read(cursor).unwrap_or_default();
        let textual = ["\\text", "\\textrm", "\\textnormal", "\\texttt", "\\mbox"]
            .iter()
            .any(|prefix| {
                body.trim_start()
                    .strip_prefix(prefix)
                    .is_some_and(|rest| rest.starts_with('{'))
            });
        if !name.is_empty() && (!has_arguments || textual) {
            self.push(
                Element::Macro {
                    name: name.clone(),
                    replacement: if has_arguments {
                        "\\text".to_string()
                    } else if command == "DeclareMathOperator" {
                        format!("\\operatorname{{{body}}}")
                    } else {
                        body.clone()
                    },
                },
                line,
            );
        }
        if !has_arguments {
            self.heading_alias(&name, &body, command != "providecommand", line);
        }
    }

    /// Resolve simple heading aliases without executing arbitrary TeX or assuming macro names.
    fn heading_alias(&mut self, name: &str, body: &str, replace: bool, line: usize) {
        let mut cursor = Cursor::new(body.trim());
        if !cursor.eat("\\") {
            return;
        }
        let command = cursor.take_while(|character| character.is_ascii_alphabetic());
        let Command::Section(level) = Command::of(&command) else {
            return;
        };
        cursor.eat("*");
        drop(BRACKET.read(&mut cursor));
        if let Some(title) = BRACE.read(&mut cursor) {
            self.push(
                Element::HeadingMacro {
                    name: name.to_string(),
                    level,
                    title,
                    replace,
                },
                line,
            );
        }
    }

    /// Consume an environment's two implementation groups without executing their commands.
    fn environment_kind(&mut self, cursor: &mut Cursor<'_>) {
        drop(BRACE.read(cursor));
        while BRACKET.read(cursor).is_some() {}
        drop(BRACE.read(cursor));
        drop(BRACE.read(cursor));
    }

    /// Record the body style a theorem declaration actually uses, including custom styles.
    fn theorem_style_kind(&mut self, cursor: &mut Cursor<'_>) {
        let Some(name) = BRACE.read(cursor) else {
            return;
        };
        let arguments: Vec<String> = (0..8).filter_map(|_| BRACE.read(cursor)).collect();
        if let Some(font) = arguments.get(2) {
            self.theorem_styles.insert(
                name,
                font.contains("\\itshape") || font.contains("\\slshape"),
            );
        }
    }

    /// Emit the labels, references and citations one consumed argument carries.
    fn nested(&mut self, body: &str, line: usize) {
        if !body.contains('\\') {
            return;
        }
        let read = Self::read(&CorpusFile {
            path: self.path.clone(),
            text: body.to_string(),
        });
        for located in read {
            if !matches!(
                located.element,
                Element::Text(_) | Element::ParagraphBreak | Element::RowBreak
            ) {
                self.push(located.element, line);
            }
        }
    }

    /// End the paragraph when the line the cursor closes was followed by a blank one.
    fn newline(&mut self, cursor: &mut Cursor<'_>) {
        let line = cursor.line();
        cursor.bump();
        let blank = cursor.take_while(char::is_whitespace);
        if blank.contains('\n') {
            self.push(Element::ParagraphBreak, line);
        } else {
            self.text.push(' ');
        }
    }

    /// Open one environment, reading a raw body when the environment holds one.
    fn open_environment(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        let Some(name) = BRACE.read(cursor) else {
            return;
        };
        let kind = name.trim().to_string();
        if kind == "document" {
            self.push(Element::BodyStart, line);
        }
        self.push(Element::EnvironmentOpen(kind.clone()), line);
        self.arguments(&kind, cursor, line);
        self.raw(&kind, cursor, line);
    }

    /// Record one element at the line it was read from, after the prose that preceded it.
    ///
    /// Running text accumulates until something ends it, so an element met in the middle of a
    /// sentence would otherwise be recorded before the sentence it sits in. Closing the run first
    /// is what makes the element stream the order a reader actually meets things in, which every
    /// rule in this family is a statement about.
    fn push(&mut self, element: Element, line: usize) {
        self.flush();
        self.elements
            .push(Located::new(element, &self.path, line.max(1)));
    }

    /// Consume the body of an environment whose content is never prose.
    ///
    /// A display environment is one math span however many lines it runs to, and a verbatim one
    /// holds text no reader reads as prose. Both are taken whole, which also stops a stray dollar
    /// or percent inside them from reopening the scanner in the wrong state.
    fn raw(&mut self, kind: &str, cursor: &mut Cursor<'_>, line: usize) {
        let role = Role::of(kind);
        if !role.is_raw() {
            return;
        }
        let body = cursor.take_until(&format!("\\end{{{kind}}}"));
        self.labels_inside(&body, line);
        if role == Role::Math {
            self.display_math(body, line);
        }
        self.push(Element::EnvironmentClose(kind.to_string()), cursor.line());
    }

    /// Emit one reference per target, since a single command may name several.
    fn reference(&mut self, command: &str, cursor: &mut Cursor<'_>, line: usize) {
        drop(BRACKET.read(cursor));
        let Some(targets) = BRACE.read(cursor) else {
            return;
        };
        for target in targets.split(',') {
            self.push(
                Element::Reference {
                    target: target.trim().to_string(),
                    command: command.to_string(),
                },
                line,
            );
        }
        self.text.push_str(" \u{b7} ");
    }

    /// Declare one numbered statement environment and whether it owes the reader a proof.
    ///
    /// Which environments are statements is a property of the document rather than of LaTeX, so
    /// it is read from the preamble that declares them. The current theorem style decides the
    /// obligation, because a plain-style environment asserts something and a definition-style one
    /// introduces a name, and only the first of those can be left unproved.
    fn statement_kind(&mut self, cursor: &mut Cursor<'_>, line: usize) {
        drop(BRACKET.read(cursor));
        let Some(name) = BRACE.read(cursor) else {
            return;
        };
        drop(BRACKET.read(cursor));
        drop(BRACE.read(cursor));
        drop(BRACKET.read(cursor));
        self.push(
            Element::StatementKind {
                name: name.trim().to_string(),
                owes_proof: self.plain_style,
            },
            line,
        );
    }

    /// Remember whether the declarations that follow assert something or introduce a name.
    fn statement_style(&mut self, cursor: &mut Cursor<'_>) {
        let style = BRACE.read(cursor).unwrap_or_default();
        self.plain_style = self
            .theorem_styles
            .get(style.trim())
            .copied()
            .unwrap_or(false);
    }

    /// End one table row, closing whatever cell text was open when it ended.
    fn row_break(&mut self, line: usize) {
        self.push(Element::RowBreak, line);
    }

    /// Read whatever sits at the cursor, which is one of six things.
    fn step(&mut self, cursor: &mut Cursor<'_>) {
        match cursor.peek() {
            Some('%') => {
                drop(cursor.take_until("\n"));
                let mut following = cursor.clone();
                drop(following.take_while(|character| matches!(character, ' ' | '\t' | '\r')));
                if following.peek() == Some('\n') {
                    self.push(Element::ParagraphBreak, cursor.line());
                }
            }
            Some('\\') => self.control(cursor),
            Some('$') => self.dollar(cursor),
            Some('\n') => self.newline(cursor),
            Some('{' | '}') => drop(cursor.bump()),
            _ => self.word(cursor),
        }
    }

    /// Take the run of ordinary characters up to the next thing the scanner reacts to.
    fn word(&mut self, cursor: &mut Cursor<'_>) {
        if self.text.trim().is_empty() {
            self.text_line = cursor.line();
        }
        self.text
            .push_str(&cursor.take_while(|character| !"%\\${}\n".contains(character)));
    }
}
