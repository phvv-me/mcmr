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
    let paragraphs = read("First paragraph.\n% provenance\n\nSecond paragraph.");
    assert!(
        paragraphs
            .iter()
            .any(|located| located.element == Element::ParagraphBreak)
    );
}

#[test]
fn unnumbered_float_captions_do_not_become_narrative_sentences() {
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}The CPU comparison matters.\
         \\captionof{figure}{Short caption.}The following paragraph has its own opening.\
         \\begin{description}\\item[Short label.]A real list sentence.\\end{description}\
         \\end{document}",
    );
    let skeleton = super::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
    let sentences = skeleton["sentences"].as_array().unwrap();
    assert_eq!(sentences.len(), 3);
    assert_eq!(sentences[0]["text"], "The CPU comparison matters.");
    assert_eq!(sentences[1]["index"], 0);
    assert_eq!(sentences[2]["text"], "A real list sentence.");
}

#[test]
fn literal_prose_macros_and_layout_arguments_keep_sentence_counts_honest() {
    let manuscript = assembled(
        "\\documentclass{article}\\newcommand{\\method}{Our method}\
         \\newcommand{\\baseline}{the CPU baseline~\\cite{baseline}}\\begin{document}\
         \\method{} compares measured tokenization rates against \\baseline{} under matched conditions.\
         \\bibliographystyle{article}\\bibliography{references}\
         \\crefalias{section}{appendix}\\numberwithin{figure}{section}\
         \\begin{adjustbox}{max width=\\linewidth}\\end{adjustbox}\
         \\captionsetup{type=table,hypcap=false}\\end{document}",
    );
    let skeleton = super::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
    let sentences = skeleton["sentences"].as_array().unwrap();
    assert_eq!(sentences.len(), 1);
    assert_eq!(sentences[0]["word_count"], 14); // The citation is one shared-reader placeholder.
    assert!(
        sentences[0]["text"]
            .as_str()
            .unwrap()
            .contains("Our method")
    );
    assert!(text::literal_macro("\\unknown{not safely expandable}").is_none());
    assert_eq!(text::words("10~words  in~this~counter"), 5);
    assert_eq!(
        text::sentences("Def. 1 supplies the input. Defs. 2 and 3 supply bounds.").len(),
        2
    );
    assert_eq!(
        text::sentences("The GPU path preserves these boundaries ( · ). Its timings differ.").len(),
        2
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
    let skeleton = super::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
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
fn a_text_mode_command_holds_words_rather_than_symbols() {
    assert_eq!(symbols::named("\\mathrm{fl}(x)"), vec!["x".to_string()]);
    assert_eq!(
        symbols::named("\\mathcal{V}"),
        vec!["\\mathcal{V}".to_string()]
    );
    assert_eq!(symbols::named("f_\\theta"), vec!["f_{\\theta}".to_string()]);
    assert_eq!(symbols::named("f_\\theta"), symbols::named("f_{\\theta}"));
    assert_eq!(symbols::named("A^\\star_{rk}"), vec!["A_{rk}"]);
    assert_eq!(symbols::named("x^{m}_i"), vec!["x_i", "m"]);
    assert_eq!(
        symbols::named("\\mathbf{A}^{\\mathsf{T}}"),
        vec!["\\mathbf{A}"]
    );
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
    let skeleton = super::skeleton::Skeleton::build(&manuscript, &walk);
    assert_eq!(walk.statements.len(), 1);
    assert_eq!(walk.statements[0]["owes_proof"], true);
    assert_eq!(walk.labels[0]["kind"], "lemma");
    assert_eq!(walk.sections[0]["title"], "Notation Index");
    assert_eq!(skeleton["paragraphs"].as_array().unwrap().len(), 5);
    assert_eq!(skeleton["statements"][0]["has_proof"], true);
    let notation = super::notation::Notation::build(&manuscript, &walk);
    assert_eq!(notation["entries"][0]["symbol"], "\\mathcal{N}");
    assert!(
        notation["entries"][0]["meaning"]
            .as_str()
            .unwrap()
            .starts_with("The node set.")
    );
    assert_eq!(notation["entries"][1]["symbol"], "x_i");
    let alpha = notation["symbols"]
        .as_array()
        .unwrap()
        .iter()
        .find(|symbol| symbol["name"] == "\\alpha_j")
        .unwrap();
    assert_eq!(alpha["use_count"], 1);
    assert_eq!(alpha["free_use_count"], 0);
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
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}\
         The unit roundoff is $u_F=1/2$.\
         For smooth reference maps $f_j$ and implemented maps $g_j$ in decoded coordinates, define the two trajectories by \\begin{equation*}h_{j+1}=f_j(h_j).\\end{equation*}\n\n\
         The \\emph{vocabulary} $\\mathcal V$ contains tokens.\n\n\
         For left operand $x_L$ and right operand $x_R$, the sum is evaluated.\n\n\
         An invalid reading makes recovery return $\\bot$ for the cell.\n\n\
         Let two nodes compute $a=A+x$ and $b=B+x$.\n\n\
         At a node, use $v_1,v_2$ for its children. Every typed domain $\\mathcal D$ has a decoder.\n\n\
         Let $\\alpha_v=1$. A bound sum is $\\sum_j\\alpha_j$; an unbound use is $\\alpha_j$.\
         \\DeclareMathOperator{\\rz}{rz}The operator is $\\rz(x)$.\n\n\
         \\section{Notation}\\begin{description}\\item[$u$] Unit roundoff. A format subscript is used when needed.\
         \\item[$w$] Weight. No format subscript is used.\\end{description}\
         \\section{Use}Now $u_{\\mathbb F}$ and $w_{\\mathbb F}$ appear.\\end{document}",
    );
    let notation = super::notation::Notation::build(&manuscript, &Walk::of(&manuscript));
    let sites = notation["sites"].as_array().unwrap();
    assert!(sites.iter().any(|site| site["symbol"] == "u_F"));
    assert!(sites.iter().any(|site| site["symbol"] == "h_j"));
    assert!(sites.iter().any(|site| site["symbol"] == "\\mathcal{V}"));
    assert!(sites.iter().any(|site| site["symbol"] == "x_L"));
    assert!(sites.iter().any(|site| site["symbol"] == "x_R"));
    assert!(!sites.iter().any(|site| site["symbol"] == "\\bot"));
    assert!(sites.iter().any(|site| site["symbol"] == "A"));
    assert!(sites.iter().any(|site| site["symbol"] == "B"));
    assert!(sites.iter().any(|site| site["symbol"] == "v_1"));
    assert!(sites.iter().any(|site| site["symbol"] == "\\mathcal{D}"));
    let names = notation["symbols"].as_array().unwrap();
    assert!(!names.iter().any(|symbol| symbol["name"] == "z"));
    let alpha = names
        .iter()
        .find(|symbol| symbol["name"] == "\\alpha_j")
        .unwrap();
    assert_eq!(alpha["use_count"], 2);
    assert_eq!(alpha["free_use_count"], 1);
    assert!(
        notation["entries"]
            .as_array()
            .unwrap()
            .iter()
            .any(|entry| entry["symbol"] == "u_{\\mathbb{F}}")
    );
    assert!(
        !notation["entries"]
            .as_array()
            .unwrap()
            .iter()
            .any(|entry| entry["symbol"] == "w_{\\mathbb{F}}")
    );
}

#[test]
fn explicit_component_bindings_do_not_export_unrelated_variants() {
    assert_eq!(
        symbols::infix("x_0\\oplus x_1"),
        Some("\\oplus".to_string())
    );
    assert!(symbols::infix("x_0\\beta x_1").is_none());
    assert!(symbols::listed("x_0,\\ldots,y_m").is_empty());
    assert!(symbols::vectors("\\mathcal a\\in\\mathbb R^m").is_empty());
    assert!(symbols::vectors("\\mathbf a+\\mathbf b\\in\\mathbb R^m").is_empty());
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
    assert!(symbols::lower_components("\\sum_{k=a}^{p-1}d_k").is_empty());
    assert!(symbols::lower_components("\\sum_{k=0}^{p-1}c + z_k").is_empty());
    let manuscript = assembled(
        "\\documentclass{article}\\newtheorem{definition}{Definition}\\begin{document}\
         \\begin{definition}The value is $m=\\sum_{k=0}^{p-1}d_k2^{-k}$, where $d_k\\in\\{0,1\\}$.\\end{definition}\
         Now $d_0$ and $d_9$ appear. The sum $\\sum_{k=0}^{p-1}q_k$ does not declare $q_0$.\n\n\
         \\begin{definition}An input primitive $\\oplus_m(x_0,\\ldots,x_{m-1})$ consumes values.\
         A block receives $\\mathbf a,\\mathbf b\\in\\mathbb R^m$, giving $x_j=a_jb_j$.\
         Let $\\mathcal C_i$ denote a group. For distinct groups $i,j\\in[K]$, compare $\\mathcal C_j$.\
         For every list of values $\\omega a_1,\\ldots,\\omega a_m$, where each $a_j$ is an integer, use $v_1,\\ldots,v_m$ for its children.\
         This uses $a_m$, $x_0$, and $v_1$.\\end{definition}\
         Outside, $a_j$, $a_m$, $x_0$, $v_1$, and $\\mathcal C_j$ remain free.\
         \\section{Notation}\\begin{description}\
         \\item[$\\mathbf x$] A vector with scalar entries $x_k$.\
         \\item[$\\mathbf w$] A vector with scalar entries $z_k$.\
         \\end{description}\\section{Other}Variants $x_j$ and $w_j$ occur.\\end{document}",
    );
    let notation = super::notation::Notation::build(&manuscript, &Walk::of(&manuscript));
    let sites = notation["sites"].as_array().unwrap();
    assert!(
        sites
            .iter()
            .any(|site| site["symbol"] == "d_0" && site["is_local"] == false)
    );
    assert!(
        !sites
            .iter()
            .any(|site| site["symbol"] == "d_9" || site["symbol"] == "q_0")
    );
    for name in ["a_j", "a_m", "x_0", "v_1", "\\mathcal{C}_j"] {
        let symbol = notation["symbols"]
            .as_array()
            .unwrap()
            .iter()
            .find(|symbol| symbol["name"] == name)
            .unwrap();
        assert_eq!(symbol["free_use_count"], 1, "{name}");
        assert!(
            !sites
                .iter()
                .any(|site| site["symbol"] == name && site["is_local"] == false),
            "{name}"
        );
    }
    let entries = notation["entries"].as_array().unwrap();
    assert!(entries.iter().any(|entry| entry["symbol"] == "x_j"));
    assert!(!entries.iter().any(|entry| entry["symbol"] == "w_j"));
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
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}\
         The measured ratio is $0.1456$, from $2.5844$ against $15.9974$. \
         The 95 percent confidence bound is $0.108$. \
         The base-128 expansion agrees \\cite{source}.\\end{document}",
    );
    let evidence = super::evidence::Evidence::build(&manuscript, &Walk::of(&manuscript));
    let numbers = evidence["numbers"].as_array().unwrap();
    assert_eq!(numbers.len(), 6);
    assert_eq!(numbers[0]["names_ratio"], true);
    assert_eq!(numbers[0]["sentence_number_count"], 3);
    assert_eq!(numbers[4]["names_ratio"], false);
    assert_eq!(numbers[5]["is_mathematical"], true);
}

#[test]
fn typst_uses_its_ast_and_refuses_unresolved_generated_content() {
    let root = tempfile::tempdir().expect("a temporary manuscript must open");
    std::fs::write(root.path().join("paper.typ"),
        "#let unused = [= Hidden heading]\n= Setup <setup>\nLet $alpha$ denote an angle.\n\n#include \"part.typ\"\n")
        .expect("the root must be writable");
    std::fs::write(root.path().join("part.typ"),
        "= Calculation\n$ bb(A)_k = alpha $ <identity>\nThe result in @identity uses @setup.\n\n= Notation\n/ $alpha$: The angle.\n")
        .expect("the part must be writable");
    let scope = crate::discovery::Scope::of(root.path(), &[".typ".to_string()]);
    let found = Manuscript::scan(root.path(), &scope).expect("literal Typst is supported");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].language, "typst");
    let walk = Walk::of(&found[0]);
    assert_eq!(walk.sections.len(), 3);
    assert_eq!(walk.sections[0]["title"], "Setup");
    assert_eq!(walk.labels[0]["name"], "setup");
    assert_eq!(walk.labels[1]["kind"], "equation");
    assert_eq!(
        super::typst::named("bb(A)_k + alpha"),
        vec!["bb(A)_k", "alpha"]
    );
    let dynamic = super::typst::TypstReader::read(&CorpusFile {
        path: "dynamic.typ".to_string(),
        text: "#show: document => document".to_string(),
    })
    .expect_err("runtime transformation must not silently pass");
    assert!(dynamic.contains("unresolved Typst"));
}

#[test]
fn literal_typst_imports_are_declarations_not_inserted_prose() {
    let root = tempfile::tempdir().expect("a temporary manuscript opens");
    std::fs::create_dir(root.path().join("chapters")).unwrap();
    std::fs::write(
        root.path().join("template.typ"),
        "#let style(body) = [= Hidden\n#body]\n",
    )
    .unwrap();
    let paper = root.path().join("chapters/paper.typ");
    std::fs::write(
        &paper,
        "#import \"../template.typ\": style\n= Visible\nLiteral text.\n",
    )
    .unwrap();
    let scope = crate::discovery::Scope::of(root.path(), &[".typ".to_string()]);
    let found = Manuscript::scan(root.path(), &scope).expect("literal import resolves");
    assert_eq!(found.len(), 1);
    assert_eq!(Walk::of(&found[0]).sections[0]["title"], "Visible");
    assert_eq!(Walk::of(&found[0]).sections.len(), 1);
    std::fs::write(
        &paper,
        "#import \"../template.typ\": style\n#style[Content]\n",
    )
    .unwrap();
    assert!(
        Manuscript::scan(root.path(), &scope)
            .err()
            .expect("a custom call needs evaluation")
            .contains("call to `style`")
    );
    std::fs::write(
        &paper,
        "#import \"../template.typ\": style as text\n#text[Content]\n",
    )
    .unwrap();
    assert!(
        Manuscript::scan(root.path(), &scope)
            .err()
            .expect("an imported name is not a builtin wrapper")
            .contains("call to `text`")
    );
}

#[test]
fn typst_import_resolution_refuses_missing_paths_and_cycles() {
    let root = tempfile::tempdir().expect("a temporary manuscript opens");
    std::fs::create_dir(root.path().join("chapters")).unwrap();
    std::fs::write(root.path().join("template.typ"), "#let value = 1\n").unwrap();
    let paper = root.path().join("chapters/paper.typ");
    std::fs::write(&paper, "#import \"template.typ\": value\n= Visible\n").unwrap();
    let scope = crate::discovery::Scope::of(root.path(), &[".typ".to_string()]);
    assert!(
        Manuscript::scan(root.path(), &scope)
            .err()
            .expect("an import cannot fall back to the project root")
            .contains("unresolved Typst import")
    );
    std::fs::write(&paper, "#import \"../template.typ\": value\n= Visible\n").unwrap();
    std::fs::write(
        root.path().join("template.typ"),
        "#import \"chapters/paper.typ\"\n#let value = 1\n",
    )
    .unwrap();
    assert!(
        Manuscript::scan(root.path(), &scope)
            .err()
            .expect("an import cycle is not an empty manuscript")
            .contains("cyclic Typst")
    );
    std::fs::write(
        &paper,
        "#let target = \"../template.typ\"\n#import target: value\n",
    )
    .unwrap();
    assert!(
        Manuscript::scan(root.path(), &scope)
            .err()
            .expect("nonliteral imports need evaluation")
            .contains("unresolved Typst")
    );
}
