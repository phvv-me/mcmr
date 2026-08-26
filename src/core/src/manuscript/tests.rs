use super::document::Manuscript;
use super::element::Element;
use super::latex::LatexReader;
use super::symbols;
use super::text;
use super::walk::Walk;
use crate::lexical::CorpusFile;

fn read(text: &str) -> Vec<super::located::Located> {
    LatexReader::read(&CorpusFile {
        path: "paper.tex".to_string(),
        text: text.to_string(),
    })
}

fn assembled(source: &str) -> Manuscript {
    let root = tempfile::tempdir().expect("a temporary manuscript must open");
    std::fs::write(root.path().join("paper.tex"), source).expect("the root must be writable");
    let scope = crate::discovery::Scope::of(root.path(), &[".tex".to_string()]);
    let mut found = Manuscript::scan(root.path(), &scope).expect("the scan must answer");
    found.pop().expect("one document class is one manuscript")
}

#[test]
fn a_comment_contributes_nothing_a_reader_reads() {
    let elements = read("visible % hidden\nmore");

    let prose: String = elements
        .iter()
        .filter_map(|located| match &located.element {
            Element::Text(body) => Some(body.clone()),
            _ => None,
        })
        .collect();
    assert!(prose.contains("visible"));
    assert!(!prose.contains("hidden"));
}

#[test]
fn a_display_environment_is_one_math_span_and_keeps_its_label() {
    let elements = read("\\begin{equation}\\label{eq:one} a = b \\end{equation}");

    assert!(
        elements
            .iter()
            .any(|located| located.element == Element::Label("eq:one".to_string()))
    );
    assert!(
        elements
            .iter()
            .any(|located| matches!(&located.element, Element::Math { display: true, .. }))
    );
}

#[test]
fn a_theorem_style_decides_whether_a_declared_environment_owes_a_proof() {
    let elements = read(
        "\\theoremstyle{plain}\\newtheorem{theorem}{Theorem}\
         \\theoremstyle{definition}\\newtheorem{example}[theorem]{Example}",
    );

    let declared: Vec<(String, bool)> = elements
        .iter()
        .filter_map(|located| match &located.element {
            Element::StatementKind { name, owes_proof } => Some((name.clone(), *owes_proof)),
            _ => None,
        })
        .collect();
    assert_eq!(
        declared,
        vec![
            ("theorem".to_string(), true),
            ("example".to_string(), false)
        ]
    );
}

#[test]
fn an_environment_argument_never_reaches_the_running_prose() {
    let elements =
        read("\\begin{table}[H]\\begin{tabular}{@{}rr@{}}one & two\\\\\\end{tabular}\\end{table}");

    let prose: String = elements
        .iter()
        .filter_map(|located| match &located.element {
            Element::Text(body) => Some(body.clone()),
            _ => None,
        })
        .collect();
    assert!(!prose.contains("rr"));
    assert!(prose.contains("one"));
}

#[test]
fn an_included_file_is_read_where_the_including_file_put_it() {
    let root = tempfile::tempdir().expect("a temporary manuscript must open");
    std::fs::write(
        root.path().join("paper.tex"),
        "\\documentclass{article}\\begin{document}before\\input{part}after\\end{document}",
    )
    .expect("the root must be writable");
    std::fs::write(root.path().join("part.tex"), "middle").expect("the part must be writable");
    let scope = crate::discovery::Scope::of(root.path(), &[".tex".to_string()]);

    let found = Manuscript::scan(root.path(), &scope).expect("the scan must answer");

    let prose: Vec<String> = found[0]
        .elements
        .iter()
        .filter_map(|located| match &located.element {
            Element::Text(body) => Some(body.trim().to_string()),
            _ => None,
        })
        .collect();
    assert_eq!(prose, vec!["before", "middle", "after"]);
}

#[test]
fn a_label_inside_a_statement_names_the_statement_and_one_inside_a_display_does_not() {
    let manuscript = assembled(
        "\\documentclass{article}\\theoremstyle{plain}\\newtheorem{theorem}{Theorem}\
         \\begin{document}\\begin{theorem}\\label{thm:one}\
         \\begin{equation}\\label{eq:one}a=b\\end{equation}\\end{theorem}\\end{document}",
    );

    let walk = Walk::of(&manuscript);

    assert_eq!(walk.statements[0]["label"], "thm:one");
    let kinds: Vec<&str> = walk
        .labels
        .iter()
        .map(|label| label["kind"].as_str().unwrap_or_default())
        .collect();
    assert_eq!(kinds, vec!["theorem", "equation"]);
}

#[test]
fn a_text_mode_command_holds_words_rather_than_symbols() {
    assert_eq!(symbols::named("\\mathrm{fl}(x)"), vec!["x".to_string()]);
    assert_eq!(symbols::named("\\mathcal{V}"), vec!["V".to_string()]);
    assert_eq!(symbols::named("f_\\theta"), vec!["f_\\theta".to_string()]);
}

#[test]
fn a_display_defines_the_symbol_standing_alone_on_its_left() {
    assert_eq!(
        symbols::defined("\\nu = \\frac{a}{b}"),
        Some("\\nu".to_string())
    );
    assert_eq!(symbols::defined("a + b = c"), None);
    assert_eq!(symbols::defined("no relation here"), None);
}

#[test]
fn a_dot_inside_a_number_or_an_abbreviation_never_ends_a_sentence() {
    assert_eq!(
        text::sentences("A value of 3.14 holds. So does Fig. 2 here.").len(),
        2
    );
    assert_eq!(
        text::numbers("reads 0.042668 against 15,997"),
        vec!["0.042668", "15,997"]
    );
    assert_eq!(text::words("three short words"), 3);
}
