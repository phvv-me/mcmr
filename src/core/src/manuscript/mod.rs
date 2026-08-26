//! Reading a mathematical manuscript as evidence rather than as source.
//!
//! A paper is a program a reader executes once, from the top, with no way to jump back. Every
//! defect this family reports is a place where that execution needs something it has not been
//! given yet, or is given two things under one name, or is told a number the evidence does not
//! carry. All three are questions about reading order and about what was defined where, so the
//! kernel establishes both once and every rule reads the answer.

use serde_json::{Value, json};

mod command;
mod cursor;
mod delimiter;
mod document;
mod element;
mod evidence;
mod include;
mod latex;
mod located;
mod notation;
mod position;
mod role;
mod skeleton;
mod symbols;
#[cfg(test)]
mod tests;
mod text;
mod walk;

pub use document::Manuscript;

use evidence::Evidence;
use notation::Notation;
use skeleton::Skeleton;
use walk::Walk;

/// The families a manuscript scan can be asked for, and what each one answers.
pub const FAMILIES: &[&str] = &[
    "ManuscriptFact",
    "ManuscriptNotationFact",
    "ManuscriptEvidenceFact",
];

/// Return the requested manuscript families, keyed by family name.
///
/// One walk answers all three, because the section a paragraph sits in, the section a symbol was
/// first met in and the section a number was printed in have to be the same section or none of
/// the comparisons between them mean anything.
pub fn facts(
    manuscripts: &[Manuscript],
    wanted: impl Fn(&str) -> bool,
) -> Vec<(String, Vec<Value>)> {
    let mut built: Vec<(String, Vec<Value>)> = FAMILIES
        .iter()
        .filter(|family| wanted(family))
        .map(|family| ((*family).to_string(), Vec::new()))
        .collect();
    for manuscript in manuscripts {
        let walk = Walk::of(manuscript);
        for (family, rows) in &mut built {
            rows.push(one(manuscript, &walk, family));
        }
    }
    built
}

/// Build one family's fact for one manuscript, with the identity every fact carries.
fn one(manuscript: &Manuscript, walk: &Walk, family: &str) -> Value {
    let mut fact = match family {
        "ManuscriptNotationFact" => Notation::build(manuscript, walk),
        "ManuscriptEvidenceFact" => Evidence::build(manuscript, walk),
        _ => Skeleton::build(manuscript, walk),
    };
    fact["key"] = json!(format!("{}:{}", family.to_lowercase(), manuscript.root));
    fact["span"] = json!({"path": manuscript.root});
    fact["language"] = json!(manuscript.language);
    fact
}
