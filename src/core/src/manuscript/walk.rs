use super::document::Manuscript;
use super::element::Element;
use super::position::Position;
use super::role::Role;
use serde_json::{Value, json};
use std::collections::BTreeMap;

/// One pass over an assembled manuscript, establishing where everything sits.
///
/// Sections, statements and floats are the three things that enclose other things, so they are
/// opened and closed here once and every other record family reads the answer. Doing it in one
/// place is what keeps a paragraph, a number and a symbol agreeing about which section they were
/// met in, which is exactly the agreement a reader relies on and a second pass would break.
pub struct Walk {
    pub positions: Vec<Position>,
    pub sections: Vec<Value>,
    pub statements: Vec<Value>,
    pub floats: Vec<Value>,
    pub labels: Vec<Value>,
    pub kinds: BTreeMap<String, bool>,
}

impl Walk {
    /// Read one manuscript's enclosing structure and the position of every element in it.
    pub fn of(manuscript: &Manuscript) -> Self {
        let mut walk = Self {
            positions: Vec::with_capacity(manuscript.elements.len()),
            sections: Vec::new(),
            statements: Vec::new(),
            floats: Vec::new(),
            labels: Vec::new(),
            kinds: Self::declared_kinds(manuscript),
        };
        let mut open = Position::opening();
        let mut stack: Vec<String> = Vec::new();
        for (order, located) in manuscript.elements.iter().enumerate() {
            open.order = order;
            walk.enter(&located.element, &mut open, &mut stack, located);
            walk.positions.push(open);
            walk.leave(&located.element, &mut open, &mut stack);
        }
        walk.attach_labels(manuscript);
        walk
    }

    /// Return one enclosing index counted from one, where zero means there was none.
    ///
    /// A record naming its section has to be able to say that it had none, and a sentinel large
    /// enough to be unmistakable is also large enough to overflow a signed column downstream.
    /// Counting from one says the same thing with a number every reader and every table holds.
    fn numbered(index: Option<usize>) -> usize {
        index.map_or(0, |at| at + 1)
    }

    /// Return the statement environments this manuscript declares, and their proof obligation.
    fn declared_kinds(manuscript: &Manuscript) -> BTreeMap<String, bool> {
        manuscript
            .elements
            .iter()
            .filter_map(|located| match &located.element {
                Element::StatementKind { name, owes_proof } => Some((name.clone(), *owes_proof)),
                _ => None,
            })
            .collect()
    }

    /// Name each label on whatever it labels, so every other pass reads one answer.
    ///
    /// A label is written after the thing it names has opened, so it cannot be attributed while
    /// that thing is being opened. Doing it in a second pass keeps a number in a table cell, a
    /// reference to that table and the table itself agreeing about what the table is called.
    fn attach_labels(&mut self, manuscript: &Manuscript) {
        for (order, located) in manuscript.elements.iter().enumerate() {
            let Element::Label(name) = &located.element else {
                continue;
            };
            let position = self.positions[order];
            let kind = self.name_target(name, &position);
            self.labels.push(json!({
                "name": name,
                "kind": kind,
                "reading_order": order,
                "path": located.path,
                "line": located.line,
                "section_number": Self::numbered(position.section),
            }));
        }
    }

    /// Write one label onto the section it opens, when it opens one.
    ///
    /// A label more than a couple of elements past its heading belongs to a display rather than
    /// to the section, since that is where an equation label sits, and calling it a section label
    /// would let a rule about unreferenced sections report the wrong thing.
    fn name_section(&mut self, name: &str, position: &Position) -> String {
        let Some(section) = position
            .section
            .and_then(|index| self.sections.get_mut(index))
        else {
            return "equation".to_string();
        };
        let opened = section["reading_order"].as_u64().unwrap_or_default() as usize;
        let named = !section["label"].as_str().unwrap_or_default().is_empty();
        if position.order.saturating_sub(opened) > 2 || named {
            return "equation".to_string();
        }
        section["label"] = json!(name);
        format!("section{}", section["level"].as_u64().unwrap_or_default())
    }

    /// Write one label onto the innermost thing it names, and return what that thing is.
    fn name_target(&mut self, name: &str, position: &Position) -> String {
        if position.in_math {
            return "equation".to_string();
        }
        if let Some(statement) = position
            .statement
            .and_then(|at| self.statements.get_mut(at))
        {
            statement["label"] = json!(name);
            return statement["kind"]
                .as_str()
                .unwrap_or("statement")
                .to_string();
        }
        if let Some(float) = position.float.and_then(|at| self.floats.get_mut(at)) {
            float["label"] = json!(name);
            return float["kind"].as_str().unwrap_or("float").to_string();
        }
        self.name_section(name, position)
    }

    /// Open whatever this element opens, before the element records its own position.
    fn enter(
        &mut self,
        element: &Element,
        open: &mut Position,
        stack: &mut Vec<String>,
        located: &super::located::Located,
    ) {
        match element {
            Element::BodyStart => open.in_body = true,
            Element::Section { level, title } => self.open_section(*level, title, open, located),
            Element::EnvironmentOpen(kind) => {
                stack.push(kind.clone());
                self.open_environment(kind, open, located);
            }
            _ => {}
        }
    }

    /// Close whatever this element closes, after the element recorded its own position.
    fn leave(&mut self, element: &Element, open: &mut Position, stack: &mut Vec<String>) {
        let Element::EnvironmentClose(kind) = element else {
            return;
        };
        while stack.pop().is_some_and(|opened| opened != *kind) {}
        match Role::of(kind) {
            Role::Cells => open.in_cells = false,
            Role::Math => open.in_math = false,
            Role::Proof => open.in_proof = false,
            Role::Figure | Role::Table => open.float = None,
            _ if self.kinds.contains_key(kind.trim_end_matches('*')) => self.close_statement(open),
            _ => {}
        }
    }

    /// Note where one statement's own environment closed, and leave it.
    fn close_statement(&mut self, open: &mut Position) {
        if let Some(statement) = open.statement.and_then(|at| self.statements.get_mut(at)) {
            statement["close_order"] = json!(open.order);
        }
        open.statement = None;
    }

    /// Record one environment and note it as the enclosing statement, float or table it is.
    fn open_environment(
        &mut self,
        kind: &str,
        open: &mut Position,
        located: &super::located::Located,
    ) {
        let base = kind.trim_end_matches('*');
        if let Some(owes_proof) = self.kinds.get(base) {
            open.statement = Some(self.statements.len());
            self.statements.push(json!({
                "reading_order": open.order,
                "kind": base,
                "label": "",
                "owes_proof": owes_proof,
                "path": located.path,
                "line": located.line,
                "section_number": Self::numbered(open.section),
                "word_count": 0,
                "proof_order": 0,
                "has_proof": false,
            }));
        }
        self.open_role(Role::of(kind), open, located);
    }

    /// Note the role an environment carries beyond being a statement.
    fn open_role(&mut self, role: Role, open: &mut Position, located: &super::located::Located) {
        match role {
            Role::Cells => open.in_cells = true,
            Role::Math => open.in_math = true,
            Role::Proof => open.in_proof = true,
            _ => {
                if let Some(float) = role.float() {
                    open.float = Some(self.floats.len());
                    self.floats.push(json!({
                        "reading_order": open.order,
                        "kind": float,
                        "label": "",
                        "path": located.path,
                        "line": located.line,
                        "caption_word_count": 0,
                    }));
                }
            }
        }
    }

    /// Record one heading and make it the section every later element belongs to.
    fn open_section(
        &mut self,
        level: u8,
        title: &str,
        open: &mut Position,
        located: &super::located::Located,
    ) {
        open.section = Some(self.sections.len());
        self.sections.push(json!({
            "reading_order": open.order,
            "level": level,
            "title": title,
            "path": located.path,
            "line": located.line,
            "word_count": 0,
            "paragraph_count": 0,
            "title_word_count": super::text::words(title),
            "label": "",
        }));
    }
}
