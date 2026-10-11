use super::{Element, Manuscript, Walk, assembled, read, symbols};

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
    let paragraphs = read("First paragraph.\n% provenance\n\nSecond paragraph.");
    assert!(
        paragraphs
            .iter()
            .any(|located| located.element == Element::ParagraphBreak)
    );
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
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}The models are \\begin{equation}\
         \\begin{gathered}x=1.\\end{gathered}\\label{eq:models}\\end{equation}\
         The next model differs.\\end{document}",
    );
    let skeleton =
        crate::manuscript::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
    assert_eq!(skeleton["sentences"].as_array().unwrap().len(), 2);
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
fn custom_statements_and_adjacent_proofs_keep_their_boundaries() {
    let manuscript = assembled(
        "\\documentclass{article}\\newtheoremstyle{custom}{0pt}{0pt}{\\itshape}{}{\\bfseries}{.}{ }{}\
         \\theoremstyle{custom}\\newmdtheoremenv[style=box]{lemma}{Lemma}\
         \\newcommand{\\notationtitle}{\\chapter{Notation Index}}\
         \\begin{document}\\begin{lemma}\\label{lem:first}First claim. Let $\\alpha_k$ denote variance.\\end{lemma}\
         \\begin{proof}First proof.\\end{proof}\\begin{proof}Second proof.\\end{proof}\
         \\notationtitle\\begin{description}\\item[$\\mathcal N$] The node set. Entries use $x_i$.\\end{description}\
         \\chapter{Appendix}\\begin{proof}[Proof of \\Cref{lem:first}] Named proof $\\sum_j\\alpha_j$.\\end{proof}\\end{document}",
    );
    let walk = Walk::of(&manuscript);
    let skeleton = crate::manuscript::skeleton::Skeleton::build(&manuscript, &walk);
    assert_eq!(
        (
            walk.statements.len(),
            skeleton["paragraphs"].as_array().unwrap().len()
        ),
        (1, 5)
    );
    assert_eq!(
        serde_json::json!([
            walk.statements[0]["owes_proof"],
            walk.labels[0]["kind"],
            walk.sections[0]["title"],
            skeleton["statements"][0]["has_proof"]
        ]),
        serde_json::json!([true, "lemma", "Notation Index", true])
    );
    let notation = crate::manuscript::notation::Notation::build(&manuscript, &walk);
    assert_eq!(
        [
            &notation["entries"][0]["symbol"],
            &notation["entries"][1]["symbol"]
        ],
        ["\\mathcal{N}", "x_i"]
    );
    assert!(
        notation["entries"][0]["meaning"]
            .as_str()
            .unwrap()
            .starts_with("The node set.")
    );
    let alpha = notation["symbols"]
        .as_array()
        .unwrap()
        .iter()
        .find(|symbol| symbol["name"] == "\\alpha_j")
        .unwrap();
    assert_eq!([&alpha["use_count"], &alpha["free_use_count"]], [1, 0]);
}

#[test]
fn a_text_mode_command_holds_words_rather_than_symbols() {
    for (source, expected) in [
        ("\\mathrm{fl}(x)", vec!["x"]),
        ("\\mathcal{V}", vec!["\\mathcal{V}"]),
        ("f_\\theta", vec!["f_{\\theta}"]),
        ("A^\\star_{rk}", vec!["A_{rk}"]),
        ("x^{m}_i", vec!["x_i", "m"]),
        ("\\mathbf{A}^{\\mathsf{T}}", vec!["\\mathbf{A}"]),
    ] {
        assert_eq!(symbols::named(source), expected, "{source}");
    }
    assert_eq!(symbols::named("f_\\theta"), symbols::named("f_{\\theta}"));
    assert_eq!(symbols::defined("f(x)=x+z"), Some("f".to_string()));
    assert_eq!(
        symbols::bound("\\sum_{k=0}^{n-1}x_k"),
        std::collections::BTreeSet::from(["k".to_string()])
    );
    assert_eq!(
        symbols::bound("\\forall i,j\\in N"),
        std::collections::BTreeSet::from(["i".to_string(), "j".to_string()])
    );
    assert_eq!(
        symbols::bound("f(x)=x+z"),
        std::collections::BTreeSet::from(["x".to_string()])
    );
    assert_eq!(
        symbols::named("\\mathcal V"),
        symbols::named("\\mathcal{V}")
    );
}
#[test]
fn markup_is_not_notation_and_different_fonts_name_different_symbols() {
    assert_eq!(
        symbols::named(
            "\\begin{aligned} \\mathbb{A}_{k} = \\boldsymbol{x}_k + \\textcolor{red}{\\beta} \\end{aligned}"
        ),
        vec!["\\mathbb{A}_k", "\\boldsymbol{x}_k", "\\beta"]
    );
    let elements =
        read("\\renewcommand\\section{\\section{Not a heading}}\\newcommand{\\number}{123}");
    assert!(
        !elements
            .iter()
            .any(|located| matches!(located.element, Element::Section { .. } | Element::Text(_)))
    );
}
#[test]
fn a_display_defines_the_symbol_standing_alone_on_its_left() {
    assert_eq!(
        symbols::defined("\\nu = \\frac{a}{b}"),
        Some("\\nu".to_string())
    );
    assert_eq!(symbols::defined("a + b = c"), None);
    assert_eq!(
        symbols::definitions(
            "b_e=0,\\qquad v_e=\\frac{h_e^2}{12},\\qquad h_e=\\operatorname{ulp}(s_e)"
        ),
        vec!["b_e", "v_e", "h_e"]
    );
    assert_eq!(
        symbols::named("\\bar{\\mathsf{s}}_{t+1}"),
        vec!["\\bar{\\mathsf{s}}_{t+1}"]
    );
    assert_eq!(
        symbols::definitions("\\begin{aligned}(\\mathbf z_t,\\bar{\\mathsf s}_{t+1}) &= f(s_t)"),
        vec!["\\mathbf{z}_t", "\\bar{\\mathsf{s}}_{t+1}"]
    );
    assert!(
        symbols::bound("\\left\\{\\mathsf{z}:f(\\mathsf{z})=0\\right\\}").contains("\\mathsf{z}")
    );
    assert_eq!(symbols::defined("no relation here"), None);
}
#[test]
fn explicit_component_bindings_do_not_export_unrelated_variants() {
    assert_eq!(
        symbols::infix("x_0\\oplus x_1"),
        Some("\\oplus".to_string())
    );
    assert!(symbols::infix("x_0\\beta x_1").is_none());
    assert!(symbols::listed("x_0,\\ldots,y_m").is_empty());
    for source in [
        "\\mathcal a\\in\\mathbb R^m",
        "\\mathbf a+\\mathbf b\\in\\mathbb R^m",
    ] {
        assert!(symbols::vectors(source).is_empty(), "{source}");
    }
    assert_eq!(
        symbols::tuple_components("\\mathbf x=(x_0,\\ldots,x_{m-1})"),
        vec!["x_0", "x_{m-1}"]
    );
    assert!(symbols::tuple_components("\\mathbf y=(x_0,\\ldots,x_{m-1})").is_empty());
    assert!(symbols::tuple_components("\\mathbf x=(2x_0,\\ldots,2x_{m-1})").is_empty());
    assert_eq!(
        symbols::lower_components("\\sum_{k=0}^{p-1}d_k\\beta^{-k} + z_k"),
        vec![("d_k".to_string(), "d_0".to_string())]
    );
    for source in ["\\sum_{k=a}^{p-1}d_k", "\\sum_{k=0}^{p-1}c + z_k"] {
        assert!(symbols::lower_components(source).is_empty(), "{source}");
    }
}
