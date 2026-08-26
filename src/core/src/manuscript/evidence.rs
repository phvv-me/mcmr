use super::document::Manuscript;
use super::element::Element;
use super::located::Located;
use super::position::Position;
use super::text;
use super::walk::Walk;
use serde_json::{Value, json};

/// The words a sentence names a derived quantity with, which is owed its two parts.
const RATIO_WORDS: &[&str] = &[
    "fraction",
    "per cent",
    "percent",
    "proportion",
    "ratio",
    "share",
    "times",
];

/// Return one caption without the mathematics set inside it.
///
/// A caption is retained whole rather than scanned, so the exponents and indices of its inline
/// mathematics would otherwise read as reported numbers. Removing the math spans leaves the
/// numbers the caption actually claims.
fn stripped(caption: &str) -> String {
    caption.split('$').step_by(2).collect::<Vec<_>>().join(" ")
}

/// The numbers one manuscript states, and where each of them was stated.
///
/// A number in running prose and the same number in a table cell are the same literal and
/// completely different claims, so each one retains the float it sits in and the section it was
/// read in. Comparing the two is what answers whether the prose agrees with the evidence, and
/// that comparison is a rule rather than something a reader should have to perform.
pub struct Evidence {
    numbers: Vec<Value>,
    citations: Vec<Value>,
    references: Vec<Value>,
    tail: String,
}

impl Evidence {
    /// Build every evidence record one manuscript states.
    pub fn build(manuscript: &Manuscript, walk: &Walk) -> Value {
        let mut evidence = Self {
            numbers: Vec::new(),
            citations: Vec::new(),
            references: Vec::new(),
            tail: String::new(),
        };
        for (order, located) in manuscript.elements.iter().enumerate() {
            let position = walk.positions[order];
            if position.in_body {
                evidence.element(located, &position, walk);
            }
        }
        json!({
            "root": manuscript.root,
            "numbers": evidence.numbers,
            "citations": evidence.citations,
            "references": evidence.references,
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

    /// Return the label of the float one position sits inside, when it sits in one.
    fn float_label(position: &Position, walk: &Walk) -> String {
        position
            .float
            .and_then(|index| walk.floats.get(index))
            .and_then(|float| float["label"].as_str())
            .unwrap_or_default()
            .to_string()
    }

    /// Whether a run of text names a quantity that is derived from two others.
    fn names_ratio(body: &str) -> bool {
        let lowered = body.to_lowercase();
        RATIO_WORDS.iter().any(|word| lowered.contains(word))
    }

    /// Record one citation and the locator it pins its source to.
    fn citation(&mut self, located: &Located, position: &Position) {
        let Element::Citation { key, pin } = &located.element else {
            return;
        };
        self.citations.push(json!({
            "key": key,
            "pin": pin,
            "reading_order": position.order,
            "path": located.path,
            "line": located.line,
            "section_number": Self::numbered(position.section),
        }));
    }

    /// Record one cross reference, which is what a number in the same section is read against.
    fn reference(&mut self, located: &Located, named: (&Position, &str, &str)) {
        let (position, target, command) = named;
        self.references.push(json!({
            "target": target,
            "command": command,
            "reading_order": position.order,
            "path": located.path,
            "line": located.line,
            "section_number": Self::numbered(position.section),
        }));
    }

    /// Record whatever numbers or sources one element states.
    fn element(&mut self, located: &Located, position: &Position, walk: &Walk) {
        match &located.element {
            Element::Text(body) => {
                self.tail = text::sentences(body).pop().unwrap_or_default();
                self.written(body, located, (position, walk));
            }
            Element::Caption(body) => self.written(&stripped(body), located, (position, walk)),
            Element::Math { text, .. } => self.computed(text, located, (position, walk)),
            Element::Citation { .. } => self.citation(located, position),
            Element::Reference { target, command } => {
                self.reference(located, (position, target, command));
            }
            _ => {}
        }
    }

    /// Record the reported quantities one math span states, in the company of the words around it.
    ///
    ///
    /// Mathematics is full of numbers that report nothing, the exponents, indices and small
    /// integer constants that make an expression rather than a measurement. A quantity a reader
    /// would check against a table carries a decimal point or several digits, so those are what
    /// is retained and the rest is arithmetic the document is doing rather than a claim.
    fn computed(&mut self, math: &str, located: &Located, context: (&Position, &Walk)) {
        let reported = text::numbers(math)
            .into_iter()
            .filter(|literal| literal.contains('.') || literal.len() > 2)
            .collect::<Vec<_>>()
            .join(" ");
        if reported.is_empty() {
            return;
        }
        let sentence = format!("{} {reported}", self.tail);
        self.written(&sentence, located, context);
    }

    /// Record every number one run of text states, with the company it kept.
    fn written(&mut self, body: &str, located: &Located, context: (&Position, &Walk)) {
        let (position, walk) = context;
        let float = Self::float_label(position, walk);
        for sentence in text::sentences(body) {
            let stated = text::numbers(&sentence);
            for literal in &stated {
                self.numbers.push(json!({
                    "literal": literal,
                    "reading_order": position.order,
                    "path": located.path,
                    "line": located.line,
                    "section_number": Self::numbered(position.section),
                    "in_cells": position.in_cells,
                    "float_label": float,
                    "names_ratio": Self::names_ratio(&sentence),
                    "sentence_number_count": stated.len(),
                }));
            }
        }
    }
}
