use super::document::Manuscript;
use super::element::Element;
use super::located::Located;
use super::position::Position;
use super::symbols;
use super::walk::Walk;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

/// The words that introduce a symbol in running prose rather than merely use one.
const CUES: &[&str] = &[
    "be", "call", "called", "define", "defined", "defines", "denote", "denoted", "denotes", "let",
    "where", "with", "write", "writes", "written", "choose", "fix", "take", "put", "set",
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
    language: String,
    aliases: BTreeMap<String, String>,
    symbols: BTreeMap<String, Value>,
    sites: Vec<Value>,
    terms: BTreeMap<String, Value>,
    entries: Vec<Value>,
    locals: BTreeSet<String>,
    endpoints: BTreeMap<String, BTreeSet<String>>,
    continued_declaration: bool,
}

impl Notation {
    /// Build every notation record one manuscript states.
    pub fn build(manuscript: &Manuscript, walk: &Walk) -> Value {
        let mut notation = Self {
            language: manuscript.language.clone(),
            aliases: manuscript
                .elements
                .iter()
                .filter_map(|located| match &located.element {
                    Element::Macro { name, replacement } => {
                        Some((name.clone(), replacement.clone()))
                    }
                    _ => None,
                })
                .collect(),
            symbols: BTreeMap::new(),
            sites: Vec::new(),
            terms: BTreeMap::new(),
            entries: Vec::new(),
            locals: BTreeSet::new(),
            endpoints: BTreeMap::new(),
            continued_declaration: false,
        };
        notation.collect(manuscript, walk);
        notation.cover_format_parameters();
        notation.cover_vector_components();
        notation.count_term_uses(manuscript, walk);
        json!({
            "root": manuscript.root,
            "symbols": notation.symbols.values().collect::<Vec<_>>(),
            "sites": notation.sites,
            "terms": notation.terms.values().collect::<Vec<_>>(),
            "entries": notation.entries,
        })
    }

    fn named(&self, text: &str) -> Vec<String> {
        if self.language == "typst" {
            super::typst::named(text)
        } else {
            symbols::named(&symbols::expanded(text, &self.aliases))
        }
    }

    fn defined(&self, text: &str) -> Vec<String> {
        if self.language != "typst" {
            return symbols::definitions(&symbols::expanded(text, &self.aliases));
        }
        let Some((left, _)) = text.split_once('=') else {
            return Vec::new();
        };
        let mut named = self.named(left);
        (named.len() == 1)
            .then(|| named.remove(0))
            .into_iter()
            .collect()
    }

    /// Return one enclosing index counted from one, where zero means there was none.
    ///
    /// A record naming its section has to be able to say that it had none, and a sentinel large
    /// enough to be unmistakable is also large enough to overflow a signed column downstream.
    /// Counting from one says the same thing with a number every reader and every table holds.
    fn numbered(index: Option<usize>) -> usize {
        index.map_or(0, |at| at + 1)
    }

    /// An index includes nested headings until the next heading at its own or a higher level.
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
        let level = walk.sections[found]["level"].as_u64().unwrap_or_default();
        let closed = walk
            .sections
            .iter()
            .skip(found + 1)
            .find(|section| section["level"].as_u64().unwrap_or_default() <= level)
            .and_then(|section| section["reading_order"].as_u64())
            .map_or(usize::MAX, |order| order as usize);
        Some((opened as usize, closed))
    }

    /// Whether the words just before a math span introduce the symbols inside it.
    fn is_cued(&self, tail: &str) -> bool {
        let tail = super::text::sentences(tail)
            .last()
            .map_or("", String::as_str)
            .to_lowercase();
        let words: Vec<_> = tail
            .split_whitespace()
            .map(|word| word.trim_matches(|c: char| !c.is_alphanumeric()))
            .filter(|word| !word.is_empty())
            .collect();
        let clause = tail.rsplit([',', ';']).next().unwrap_or_default();
        words.first().is_some_and(|word| {
            CUES.contains(word) || matches!(*word, "assume" | "suppose" | "given")
        }) || clause
            .split_whitespace()
            .next()
            .is_some_and(|word| CUES.contains(&word))
            || tail.trim_start().starts_with("for each ")
            || tail.trim_start().starts_with("for every ")
            || self
                .terms
                .contains_key(tail.trim().trim_end_matches('·').trim_end())
            || words
                .iter()
                .rev()
                .take(CUE_REACH)
                .any(|word| CUES.contains(word))
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
            if index.is_some_and(|(opened, closed)| (opened..closed).contains(&position.order)) {
                self.index_row(located, &position, &mut row);
                continue;
            }
            if !row.is_empty() {
                self.push_entry(std::mem::take(&mut row), located);
            }
            let following = Self::following_text(&manuscript.elements[order + 1..]);
            let local = position.in_proof
                || position.statement.is_some_and(|statement| {
                    matches!(
                        walk.statements[statement]["kind"].as_str(),
                        Some("theorem" | "lemma" | "proposition" | "corollary")
                    )
                });
            if (!position.in_proof && position.statement.is_none())
                || matches!(&located.element, Element::EnvironmentOpen(name) | Element::EnvironmentClose(name) if matches!(name.as_str(), "proof" | "theorem" | "lemma" | "proposition" | "corollary" | "definition"))
            {
                self.locals.clear();
                self.endpoints.clear();
            }
            if matches!(&located.element, Element::EnvironmentOpen(kind) if kind == "proof")
                && let Some(target) = manuscript.proof_target(order)
                && let Some(statement) = walk
                    .statements
                    .iter()
                    .position(|statement| statement["label"] == target)
            {
                self.locals.extend(
                    self.sites
                        .iter()
                        .filter(|site| {
                            site["statement_number"] == statement + 1 && site["is_local"] == true
                        })
                        .filter_map(|site| site["symbol"].as_str().map(str::to_string)),
                );
            }
            self.element(located, &position, &tail, &following, local);
            match &located.element {
                Element::Text(body) => tail = body.clone(),
                Element::EnvironmentOpen(kind)
                    if super::role::Role::of(kind) == super::role::Role::Math => {}
                Element::ParagraphBreak
                | Element::RowBreak
                | Element::Section { .. }
                | Element::EnvironmentOpen(_)
                | Element::EnvironmentClose(_) => {
                    tail.clear();
                    self.continued_declaration = false;
                }
                _ => {}
            }
        }
        if let Some(located) = manuscript.elements.last() {
            self.push_entry(row, located);
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
    fn element(
        &mut self,
        located: &Located,
        position: &Position,
        tail: &str,
        following: &str,
        local: bool,
    ) {
        match &located.element {
            Element::Math { text, display } => {
                self.math(text, located, (position, *display, tail), following, local)
            }
            Element::Emphasis { command, marked } => {
                self.term(marked, located, (position, command))
            }
            Element::Caption(body) if self.language == "latex" => {
                let spans = super::latex::LatexReader::read(&crate::lexical::CorpusFile {
                    path: located.path.clone(),
                    text: body.clone(),
                });
                for span in spans {
                    if let Element::Math { text, .. } = span.element {
                        for symbol in self.defined(&text) {
                            self.sites.push(json!({"symbol": symbol, "reading_order": position.order, "path": located.path, "line": located.line + span.line - 1, "section_number": Self::numbered(position.section), "statement_number": 0, "is_display": false, "meaning": "", "is_local": false}));
                        }
                    }
                }
            }
            _ => {}
        }
    }

    /// A definition's role can follow its symbol; stop at the next formula or structural boundary.
    fn following_text(elements: &[Located]) -> String {
        let mut text = String::new();
        for located in elements {
            match &located.element {
                Element::Text(body) => {
                    text.push_str(body);
                    if super::text::sentences(&text).len() > 1 || body.trim_end().ends_with('.') {
                        break;
                    }
                }
                Element::MacroUse(_) | Element::Emphasis { .. } => {}
                _ => break,
            }
        }
        super::text::sentences(&text)
            .first()
            .cloned()
            .unwrap_or_default()
    }

    /// Compare explicit role phrases, not arbitrary equation equivalence or bare assignments.
    fn meaning(&self, tail: &str, following: &str) -> String {
        let sentences = super::text::sentences(tail);
        let before = sentences
            .last()
            .map_or("", String::as_str)
            .trim()
            .trim_end_matches('·')
            .trim()
            .to_lowercase();
        let after = following.trim().to_lowercase();
        let role = [
            "denote ",
            "denotes ",
            "be ",
            "means ",
            "represents ",
            "stand for ",
            "stands for ",
        ]
        .iter()
        .find_map(|prefix| after.strip_prefix(prefix))
        .or_else(|| {
            self.is_cued(tail)
                .then(|| after.strip_prefix("for "))
                .flatten()
        })
        .or_else(|| self.terms.contains_key(&before).then_some(before.as_str()))
        .or_else(|| {
            let role = before
                .strip_prefix("for ")
                .or_else(|| before.strip_prefix("and "))
                .or_else(|| before.strip_prefix("every "))
                .or_else(|| before.strip_prefix("each "))?;
            let words: Vec<_> = role.split_whitespace().collect();
            (words.len() <= 4
                && words.last().is_some_and(|word| {
                    matches!(
                        *word,
                        "operand"
                            | "vector"
                            | "matrix"
                            | "scalar"
                            | "function"
                            | "operator"
                            | "index"
                            | "node"
                            | "set"
                            | "domain"
                    )
                }))
            .then_some(role)
        })
        .or_else(|| {
            after
                .starts_with("in which")
                .then(|| {
                    [" have an ", " have a ", " has an ", " has a "]
                        .iter()
                        .find_map(|prefix| before.rsplit_once(prefix).map(|(_, role)| role))
                })
                .flatten()
        });
        let Some(role) = role else {
            return String::new();
        };
        let role = role.trim().trim_end_matches(['.', ',', ';', ':']);
        if !role.chars().any(char::is_alphabetic) {
            return String::new();
        }
        let role = ["the ", "a ", "an "]
            .iter()
            .find_map(|prefix| role.strip_prefix(prefix))
            .unwrap_or(role);
        role.split_whitespace().collect::<Vec<_>>().join(" ")
    }

    /// Record one row of the notation index as an entry per symbol it names.
    ///
    /// The first cell of a row holds the symbols and the rest hold the meaning, so the row is
    /// split at the first cell separator the reader sees. A row naming several symbols is one
    /// entry per symbol, since that is how a reader looks one up.
    fn index_row(&mut self, located: &Located, position: &Position, row: &mut Vec<Value>) {
        if let Element::ItemLabel(label) = &located.element {
            self.push_entry(std::mem::take(row), located);
            let names: Vec<String> = label
                .split('$')
                .skip(1)
                .step_by(2)
                .flat_map(|text| self.named(text))
                .collect();
            row.push(json!(names));
            row.push(json!("&"));
            return;
        }
        if !position.in_cells && row.is_empty() {
            return;
        }
        match &located.element {
            Element::Math { text, .. } => row.push(json!(self.named(text))),
            Element::Text(text) => row.push(json!(text)),
            Element::RowBreak | Element::EnvironmentClose(_) => {
                self.push_entry(std::mem::take(row), located)
            }
            _ => {}
        }
    }

    /// Record one math span's symbols, and the site when the span introduces them.
    fn math(
        &mut self,
        text: &str,
        located: &Located,
        context: (&Position, bool, &str),
        following: &str,
        local: bool,
    ) {
        let (position, display, tail) = context;
        let connective = tail.trim().trim_end_matches('·').trim();
        let cued = self.is_cued(tail)
            || (connective.split_whitespace().last() == Some("use")
                && following.trim_start().starts_with("for "))
            || (self.continued_declaration && matches!(connective, "and" | "or" | "," | ", and"));
        self.continued_declaration = cued;
        let mut introduced = self.defined(text);
        let meaning = self.meaning(tail, following);
        let names = self.named(text);
        let expanded = symbols::expanded(text, &self.aliases);
        let infix = (self.language == "latex"
            && ["denotes ", "means "]
                .iter()
                .any(|cue| following.trim_start().starts_with(cue)))
        .then(|| symbols::infix(&expanded))
        .flatten();
        introduced.extend(infix.iter().cloned());
        let subject = infix.as_ref().or_else(|| names.first());
        let bound = if self.language == "latex" {
            symbols::bound(&expanded)
        } else {
            Default::default()
        };
        if self.language == "latex" {
            introduced.extend(symbols::tuple_components(&expanded));
            for (family, endpoint) in symbols::lower_components(&expanded) {
                self.endpoints.entry(family).or_default().insert(endpoint);
            }
            if position.statement.is_some() {
                self.locals.extend(symbols::vectors(&expanded));
                let before = super::text::sentences(connective)
                    .last()
                    .map_or("", String::as_str)
                    .trim()
                    .to_lowercase();
                if before.starts_with("for ")
                    && let Some((indices, _)) = expanded.split_once("\\in")
                    && indices
                        .chars()
                        .all(|one| one.is_ascii_alphabetic() || one.is_whitespace() || one == ',')
                {
                    self.locals
                        .extend(symbols::bound(&format!("\\forall {indices}")));
                }
                let quantified = before
                    .split_whitespace()
                    .any(|word| matches!(word, "every" | "each"));
                let parameters = before.trim_end().ends_with("primitive")
                    || (cued && following.trim_start().starts_with("for "));
                if quantified || parameters {
                    self.locals.extend(symbols::listed(&expanded));
                    if quantified && names.len() == 1 {
                        self.locals.extend(names.iter().cloned());
                    }
                }
            }
        }
        for name in &names {
            let declaration = cued
                || introduced.contains(name)
                || (!meaning.is_empty() && subject == Some(name));
            if local && declaration {
                self.locals.insert(name.clone());
            }
            let local_family = symbols::indexed(name).is_some_and(|(base, index)| {
                self.locals.contains(&format!("\\mathbf{{{base}}}"))
                    || ((bound.contains(index) || self.locals.contains(index))
                        && (self.locals.iter().any(|local| {
                            symbols::indexed(local).is_some_and(|(declared, _)| base == declared)
                        }) || self.sites.iter().any(|site| {
                            site["is_local"] == false
                                && site["symbol"]
                                    .as_str()
                                    .and_then(symbols::indexed)
                                    .is_some_and(|(declared, _)| base == declared)
                        })))
            });
            self.see(
                name,
                located,
                position,
                !bound.contains(name) && !self.locals.contains(name) && !local_family,
            );
            if declaration || bound.contains(name) {
                let site = json!({
                    "symbol": name,
                    "reading_order": position.order,
                    "path": located.path,
                    "line": located.line,
                    "section_number": Self::numbered(position.section),
                    "statement_number": Self::numbered(position.statement),
                    "is_display": display,
                    "meaning": if subject == Some(name) { meaning.as_str() } else { "" },
                    "is_local": local || bound.contains(name) || self.locals.contains(name) || local_family,
                });
                if declaration
                    && site["is_local"] == false
                    && let Some(endpoints) = self.endpoints.get(name)
                {
                    for endpoint in endpoints {
                        let mut specialized = site.clone();
                        specialized["symbol"] = json!(endpoint);
                        self.sites.push(specialized);
                    }
                }
                self.sites.push(site);
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
                Value::Array(spans) => {
                    named.extend(Self::spelled(spans));
                    if cell > 0 {
                        meaning.push_str(" · ");
                    }
                }
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

    /// An explicit format-subscript convention covers only domain-styled parameters of its entries.
    fn cover_format_parameters(&mut self) {
        let mut covered = Vec::new();
        for entry in &self.entries {
            if !entry["meaning"]
                .as_str()
                .unwrap_or_default()
                .to_lowercase()
                .contains("a format subscript is used")
            {
                continue;
            }
            let Some(base) = entry["symbol"].as_str() else {
                continue;
            };
            for symbol in self.symbols.keys() {
                if symbol.strip_prefix(base).is_some_and(|script| {
                    script.starts_with("_{\\mathbb{") && script.ends_with("}}")
                }) {
                    let mut parameterized = entry.clone();
                    parameterized["symbol"] = json!(symbol);
                    covered.push(parameterized);
                }
            }
        }
        self.entries.extend(covered);
    }

    /// An index row explicitly pairing vectors with scalar entries covers their simple components.
    fn cover_vector_components(&mut self) {
        let mut covered = Vec::new();
        for entry in &self.entries {
            if !entry["meaning"]
                .as_str()
                .unwrap_or_default()
                .to_lowercase()
                .contains("with scalar entries")
            {
                continue;
            }
            let Some((base, _)) = entry["symbol"].as_str().and_then(symbols::indexed) else {
                continue;
            };
            if !self.entries.iter().any(|vector| {
                vector["path"] == entry["path"]
                    && vector["line"] == entry["line"]
                    && vector["symbol"] == format!("\\mathbf{{{base}}}")
            }) {
                continue;
            }
            for name in self.symbols.keys() {
                let Some((family, index)) = name.rsplit_once('_') else {
                    continue;
                };
                if family == base
                    && index.len() == 1
                    && index.chars().all(|one| one.is_ascii_alphanumeric())
                {
                    let mut component = entry.clone();
                    component["symbol"] = json!(name);
                    covered.push(component);
                }
            }
        }
        self.entries.extend(covered);
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
    fn see(&mut self, name: &str, located: &Located, position: &Position, free: bool) {
        let record = self.symbols.entry(name.to_string()).or_insert_with(|| {
            json!({
                "name": name,
                "first_order": position.order,
                "path": located.path,
                "line": located.line,
                "use_count": 0,
                "section_count": 0,
                "last_section": 0,
                "free_use_count": 0,
                "free_section_count": 0,
                "first_free_order": 0,
                "last_free_section": 0,
            })
        });
        let previous = record["use_count"].as_u64().unwrap_or_default();
        record["use_count"] = json!(previous + 1);
        let section = Self::numbered(position.section);
        if free {
            let count = record["free_use_count"].as_u64().unwrap_or_default();
            if count == 0 {
                record["first_free_order"] = json!(position.order);
                record["path"] = json!(located.path);
                record["line"] = json!(located.line);
            }
            record["free_use_count"] = json!(count + 1);
            if record["last_free_section"] != json!(section) {
                record["free_section_count"] =
                    json!(record["free_section_count"].as_u64().unwrap_or_default() + 1);
                record["last_free_section"] = json!(section);
            }
        }
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
