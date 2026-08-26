use super::document::Manuscript;
use super::element::Element;
use super::located::Located;
use super::position::Position;
use super::role::Role;
use super::text;
use super::walk::Walk;
use serde_json::{Value, json};

/// How far past a statement a proof or a run-in head still reads as that statement's argument.
const HEAD_REACH: usize = 6;

/// How many characters of what follows a statement are kept as its discharge head.
const HEAD_WIDTH: usize = 48;

/// The skeleton of one manuscript, as records a rule can join.
///
/// Everything here is an observation rather than a verdict. A reference retains where it points
/// rather than a claim that it points forwards, and a statement retains the order of whatever
/// followed it rather than a claim that it is unproved, because whether either is a defect is a
/// question about this project's conventions and belongs in a rule.
pub struct Skeleton {
    sections: Vec<Value>,
    statements: Vec<Value>,
    floats: Vec<Value>,
    labels: Vec<Value>,
    references: Vec<Value>,
    paragraphs: Vec<Value>,
    sentences: Vec<Value>,
}

impl Skeleton {
    /// Build every skeleton record one manuscript states.
    pub fn build(manuscript: &Manuscript, walk: &Walk) -> Value {
        let mut skeleton = Self {
            sections: walk.sections.clone(),
            statements: walk.statements.clone(),
            floats: walk.floats.clone(),
            labels: walk.labels.clone(),
            references: Vec::new(),
            paragraphs: Vec::new(),
            sentences: Vec::new(),
        };
        skeleton.collect(manuscript, walk);
        skeleton.attach_arguments(manuscript);
        json!({
            "root": manuscript.root,
            "sections": skeleton.sections,
            "statements": skeleton.statements,
            "floats": skeleton.floats,
            "labels": skeleton.labels,
            "references": skeleton.references,
            "paragraphs": skeleton.paragraphs,
            "sentences": skeleton.sentences,
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

    /// Add one element's prose to the paragraph, returning where that paragraph opened.
    fn accumulate(paragraph: &mut String, opened: usize, met: (&Located, usize)) -> usize {
        let (located, order) = met;
        let Element::Text(body) = &located.element else {
            return opened;
        };
        let started = if paragraph.trim().is_empty() {
            order
        } else {
            opened
        };
        paragraph.push_str(body);
        started
    }

    /// Record the proof and the run-in head that follow each statement, when either does.
    ///
    /// A house convention often discharges a claim with a bold head rather than with a proof
    /// environment, so both are retained and a rule decides which this project accepts. Only the
    /// few elements immediately after the statement are read, since an argument the reader meets
    /// two pages later is not one this statement carries.
    fn attach_arguments(&mut self, manuscript: &Manuscript) {
        for statement in &mut self.statements {
            let closed = statement["close_order"].as_u64().unwrap_or_default() as usize;
            for (order, located) in manuscript
                .elements
                .iter()
                .enumerate()
                .skip(closed + 1)
                .take(HEAD_REACH)
            {
                match &located.element {
                    Element::EnvironmentOpen(kind) if Role::of(kind) == Role::Proof => {
                        statement["proof_order"] = json!(order);
                    }
                    Element::Text(body) => Self::note_head(statement, body),
                    _ => {}
                }
            }
        }
    }

    /// Keep the first words that follow a statement, which is where a house head discharges it.
    ///
    /// A project that writes `Why it is true.` after a theorem has argued it, and a project that
    /// writes nothing has not. Only the opening words are kept, because a rule matching a
    /// configured head against them is checking a convention rather than reading the argument.
    fn note_head(statement: &mut Value, following: &str) {
        if !statement["discharge_head"].is_null() {
            return;
        }
        let head: String = following.trim().chars().take(HEAD_WIDTH).collect();
        if !head.is_empty() {
            statement["discharge_head"] = json!(head);
        }
    }

    /// Attach one caption to the float that carries it.
    fn caption(&mut self, caption: &str, position: &Position) {
        let Some(float) = position.float.and_then(|index| self.floats.get_mut(index)) else {
            return;
        };
        float["caption_word_count"] = json!(text::words(caption));
        float["caption"] = json!(caption);
    }

    /// Record one paragraph and its sentences, then start a new one.
    fn close_paragraph(&mut self, opened: usize, source: (&Manuscript, &Walk), body: String) {
        let (manuscript, walk) = source;
        let Some(located) = manuscript.elements.get(opened) else {
            return;
        };
        if body.trim().is_empty() {
            return;
        }
        let position = walk.positions[opened];
        let found = text::sentences(&body);
        self.record_sentences(&found, located, opened);
        self.paragraphs.push(json!({
            "reading_order": opened,
            "path": located.path,
            "line": located.line,
            "word_count": text::words(&body),
            "sentence_count": found.len(),
            "section_number": Self::numbered(position.section),
            "in_cells": position.in_cells,
            "in_float": position.float.is_some(),
        }));
    }

    /// Read every body element once, recording what it contributes to the skeleton.
    fn collect(&mut self, manuscript: &Manuscript, walk: &Walk) {
        let mut paragraph = String::new();
        let mut opened = 0usize;
        for (order, located) in manuscript.elements.iter().enumerate() {
            let position = walk.positions[order];
            if !position.in_body {
                continue;
            }
            self.element(located, &position);
            opened = Self::accumulate(&mut paragraph, opened, (located, order));
            if matches!(located.element, Element::ParagraphBreak) {
                let body = std::mem::take(&mut paragraph);
                self.close_paragraph(opened, (manuscript, walk), body);
            }
        }
        self.close_paragraph(opened, (manuscript, walk), paragraph);
    }

    /// Record whatever one element contributes beyond the prose it carries.
    fn element(&mut self, located: &Located, position: &Position) {
        match &located.element {
            Element::Reference { .. } => self.reference(located, position),
            Element::Caption(caption) => self.caption(caption, position),
            _ => {}
        }
    }

    /// Record each sentence of one paragraph beside the paragraph itself.
    fn record_sentences(&mut self, found: &[String], located: &Located, opened: usize) {
        for (index, sentence) in found.iter().enumerate() {
            self.sentences.push(json!({
                "reading_order": opened,
                "index": index,
                "path": located.path,
                "line": located.line,
                "word_count": text::words(sentence),
                "text": sentence.trim(),
            }));
        }
    }

    /// Record one cross reference where the reader meets it.
    fn reference(&mut self, located: &Located, position: &Position) {
        let Element::Reference { target, command } = &located.element else {
            return;
        };
        self.references.push(json!({
            "target": target,
            "command": command,
            "reading_order": position.order,
            "path": located.path,
            "line": located.line,
            "section_number": Self::numbered(position.section),
        }));
    }
}
