use super::document::Manuscript;
use super::element::Element;
use super::located::Located;
use super::position::Position;
use super::symbols;
use super::walk::Walk;
use serde_json::{Value, json};
use std::collections::BTreeMap;

/// The words that introduce a symbol in running prose rather than merely use one.
const CUES: &[&str] = &[
    "be", "call", "called", "define", "defined", "defines", "denote", "denoted", "denotes", "let",
    "where", "with", "write", "writes", "written",
];

/// The words a notation entry splits a symbol's senses with.
const SENSES: &[&str] = &["also", "elsewhere", "instead", "sense", "senses"];

/// How many words back a definition cue still reaches the symbol it introduces.
const CUE_REACH: usize = 4;

/// What one manuscript calls things, and where it says so.
///
/// The three record families answer the three questions a reader keeps asking. Which symbols are
/// there and where were they first met, where does the document appear to introduce one, and what
/// does its own notation index claim. Whether an introduction is a collision or an index is
/// incomplete is a comparison between these, which is a rule's work rather than a reader's.
pub struct Notation {
    symbols: BTreeMap<String, Value>,
    sites: Vec<Value>,
    terms: BTreeMap<String, Value>,
    entries: Vec<Value>,
}

impl Notation {
    /// Build every notation record one manuscript states.
    pub fn build(manuscript: &Manuscript, walk: &Walk) -> Value {
        let mut notation = Self {
            symbols: BTreeMap::new(),
            sites: Vec::new(),
            terms: BTreeMap::new(),
            entries: Vec::new(),
        };
        notation.collect(manuscript, walk);
        notation.count_term_uses(manuscript, walk);
        json!({
            "root": manuscript.root,
            "symbols": notation.symbols.values().collect::<Vec<_>>(),
            "sites": notation.sites,
            "terms": notation.terms.values().collect::<Vec<_>>(),
            "entries": notation.entries,
        })
    }

    /// Return one enclosing index counted from one, where zero means there was none.
    ///
    /// A record naming its section has to be able to say that it had none, and a sentinel large
    /// enough to be unmistakable is also large enough to overflow a signed column downstream.
    /// Counting from one says the same thing with a number every reader and every table holds.
    fn numbered(index: Option<usize>) -> usize {
        index.map_or(0, |at| at + 1)
    }

    /// Return the reading order at which the notation index opens, when the document has one.
    fn index_section(walk: &Walk) -> Option<(usize, usize)> {
        let found = walk.sections.iter().position(|section| {
            section["title"]
                .as_str()
                .unwrap_or_default()
                .to_lowercase()
                .contains("notation")
        })?;
        let opened = walk.sections[found]["reading_order"]
            .as_u64()
            .unwrap_or_default();
        Some((found, opened as usize))
    }

    /// Whether the words just before a math span introduce the symbols inside it.
    fn is_cued(tail: &str) -> bool {
        tail.to_lowercase()
            .split_whitespace()
            .rev()
            .take(CUE_REACH)
            .any(|word| CUES.contains(&word.trim_matches(|c: char| !c.is_alphanumeric())))
    }

    /// Read every element once, recording the symbols, terms and index rows it states.
    fn collect(&mut self, manuscript: &Manuscript, walk: &Walk) {
        let index = Self::index_section(walk);
        let mut tail = String::new();
        let mut row: Vec<Value> = Vec::new();
        for (order, located) in manuscript.elements.iter().enumerate() {
            let position = walk.positions[order];
            if !position.in_body {
                continue;
            }
            if index.is_some_and(|(section, _)| position.section == Some(section)) {
                self.index_row(located, &position, &mut row);
                continue;
            }
            self.element(located, &position, &tail);
            if let Element::Text(body) = &located.element {
                tail = body.clone();
            }
        }
    }

    /// Count where and how often each marked term is used anywhere in the body prose.
    ///
    /// A term is introduced by marking it, so a use that precedes the mark is a reader meeting a
    /// name before being told what it means. Finding that needs the first use rather than a
    /// total, which is why the body is read in order rather than joined into one string.
    fn count_term_uses(&mut self, manuscript: &Manuscript, walk: &Walk) {
        for (order, located) in manuscript.elements.iter().enumerate() {
            let Element::Text(text) = &located.element else {
                continue;
            };
            if !walk.positions[order].in_body {
                continue;
            }
            let lowered = text.to_lowercase();
            for (term, record) in &mut self.terms {
                Self::note_use(record, &lowered, (term, order));
            }
        }
    }

    /// Whether one match of a term stands as its own word rather than inside a longer one.
    ///
    /// Counting `state` inside `statement` and `stated` turns an ordinary word into the most used
    /// term in the document, which is enough on its own to make every count meaningless.
    fn is_whole_word(lowered: &str, term: &str, at: usize) -> bool {
        let before = lowered[..at].chars().next_back();
        let after = lowered[at + term.len()..].chars().next();
        !before.is_some_and(|one| one.is_alphanumeric())
            && !after.is_some_and(|one| one.is_alphanumeric())
    }

    /// Record one text run's uses of a term, keeping the first place the reader met it.
    fn note_use(record: &mut Value, lowered: &str, met: (&str, usize)) {
        let (term, order) = met;
        let seen = lowered
            .match_indices(term)
            .filter(|(at, _)| Self::is_whole_word(lowered, term, *at))
            .count();
        if seen == 0 {
            return;
        }
        let counted = record["use_count"].as_u64().unwrap_or_default();
        record["use_count"] = json!(counted + seen as u64);
        if record["first_use_order"].as_u64().unwrap_or_default() == 0 {
            record["first_use_order"] = json!(order);
        }
    }

    /// Record whatever one element says about what things are called.
    fn element(&mut self, located: &Located, position: &Position, tail: &str) {
        match &located.element {
            Element::Math { text, display } => {
                self.math(text, located, (position, *display, tail))
            }
            Element::Emphasis { command, marked } => {
                self.term(marked, located, (position, command))
            }
            _ => {}
        }
    }

    /// Record one row of the notation index as an entry per symbol it names.
    ///
    /// The first cell of a row holds the symbols and the rest hold the meaning, so the row is
    /// split at the first cell separator the reader sees. A row naming several symbols is one
    /// entry per symbol, since that is how a reader looks one up.
    fn index_row(&mut self, located: &Located, position: &Position, row: &mut Vec<Value>) {
        if !position.in_cells {
            return;
        }
        match &located.element {
            Element::Math { text, .. } => row.push(json!(symbols::named(text))),
            Element::Text(text) => row.push(json!(text)),
            Element::RowBreak => self.push_entry(std::mem::take(row), located),
            _ => {}
        }
    }

    /// Record one math span's symbols, and the site when the span introduces them.
    fn math(&mut self, text: &str, located: &Located, context: (&Position, bool, &str)) {
        let (position, display, tail) = context;
        let cued = Self::is_cued(tail);
        let introduced = symbols::defined(text).filter(|_| display);
        for name in symbols::named(text) {
            self.see(&name, located, position);
            if cued || introduced.as_deref() == Some(name.as_str()) {
                self.sites.push(json!({
                    "symbol": name,
                    "reading_order": position.order,
                    "path": located.path,
                    "line": located.line,
                    "section_number": Self::numbered(position.section),
                    "statement_number": Self::numbered(position.statement),
                    "is_display": display,
                }));
            }
        }
    }

    /// Record one notation index entry per symbol the row names.
    ///
    /// A row states its symbols in the first cell and what they mean in the rest, so it is split
    /// at the first cell separator and everything after it is the meaning. A row whose first cell
    /// names no symbol is a rule, a header or a note, and states nothing to index.
    fn push_entry(&mut self, row: Vec<Value>, located: &Located) {
        let mut named: Vec<String> = Vec::new();
        let mut meaning = String::new();
        let mut cell = 0usize;
        for item in &row {
            match item {
                Value::Array(spans) if cell == 0 => named.extend(Self::spelled(spans)),
                Value::String(text) => cell = Self::read_cell(text, cell, &mut meaning),
                _ => {}
            }
        }
        let lowered = meaning.to_lowercase();
        let senses = SENSES.iter().filter(|word| lowered.contains(*word)).count() + 1;
        named.dedup();
        for symbol in named {
            self.entries.push(json!({
                "symbol": symbol,
                "meaning": meaning.trim(),
                "sense_count": senses,
                "path": located.path,
                "line": located.line,
            }));
        }
    }

    /// Add one text run to the meaning, returning which cell of the row it ended in.
    fn read_cell(text: &str, cell: usize, meaning: &mut String) -> usize {
        let mut at = cell;
        for (index, part) in text.split('&').enumerate() {
            at += usize::from(index > 0);
            if at > 0 {
                meaning.push_str(part);
            }
        }
        at
    }

    /// Return the symbols one cell's math spans spell.
    fn spelled(spans: &[Value]) -> Vec<String> {
        spans
            .iter()
            .filter_map(Value::as_str)
            .map(str::to_string)
            .collect()
    }

    /// Note that one symbol was met, keeping where the reader first met it.
    fn see(&mut self, name: &str, located: &Located, position: &Position) {
        let record = self.symbols.entry(name.to_string()).or_insert_with(|| {
            json!({
                "name": name,
                "first_order": position.order,
                "path": located.path,
                "line": located.line,
                "use_count": 0,
                "section_count": 0,
                "last_section": 0,
            })
        });
        let previous = record["use_count"].as_u64().unwrap_or_default();
        record["use_count"] = json!(previous + 1);
        let section = Self::numbered(position.section);
        if record["last_section"].as_u64().unwrap_or_default() as usize != section {
            let seen = record["section_count"].as_u64().unwrap_or_default();
            record["section_count"] = json!(seen + 1);
            record["last_section"] = json!(section);
        }
    }

    /// Record one marked phrase as a term this document introduces.
    fn term(&mut self, marked: &str, located: &Located, context: (&Position, &str)) {
        let (position, command) = context;
        let term = marked.trim().trim_end_matches('.').to_lowercase();
        let words = term.split_whitespace().count();
        let spelled = term
            .chars()
            .any(|one| "$\\{}".contains(one) || one.is_ascii_digit());
        if term.len() < 4 || words > 4 || spelled {
            return;
        }
        self.terms.entry(term.clone()).or_insert_with(|| {
            json!({
                "term": term,
                "command": command,
                "mark_order": position.order,
                "path": located.path,
                "line": located.line,
                "use_count": 0,
                "first_use_order": 0,
                "section_number": Self::numbered(position.section),
            })
        });
    }
}
