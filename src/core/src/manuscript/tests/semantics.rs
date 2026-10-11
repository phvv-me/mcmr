use super::{Walk, assembled, symbols, text};

#[test]
fn unnumbered_float_captions_do_not_become_narrative_sentences() {
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}The CPU comparison matters.\
         \\captionof{figure}{Short caption.}The following paragraph has its own opening.\
         \\begin{description}\\item[Short label.]A real list sentence.\\end{description}\
         \\end{document}",
    );
    let skeleton =
        crate::manuscript::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
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
    let skeleton =
        crate::manuscript::skeleton::Skeleton::build(&manuscript, &Walk::of(&manuscript));
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
        text::sentences("The GPU path preserves these boundaries ( · ). Its timings differ.")
            .len(),
        2
    );
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
    let evidence =
        crate::manuscript::evidence::Evidence::build(&manuscript, &Walk::of(&manuscript));
    let numbers = evidence["numbers"].as_array().unwrap();
    assert_eq!(numbers.len(), 6);
    assert_eq!(
        serde_json::json!([
            numbers[0]["names_ratio"],
            numbers[0]["sentence_number_count"],
            numbers[4]["names_ratio"],
            numbers[5]["is_mathematical"]
        ]),
        serde_json::json!([true, 3, false, true])
    );
}

#[test]
fn explicit_introductions_distinguish_free_uses_and_index_conventions() {
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
    let notation =
        crate::manuscript::notation::Notation::build(&manuscript, &Walk::of(&manuscript));
    let sites = notation["sites"].as_array().unwrap();
    for name in [
        "u_F",
        "h_j",
        "\\mathcal{V}",
        "x_L",
        "x_R",
        "A",
        "B",
        "v_1",
        "\\mathcal{D}",
    ] {
        assert!(sites.iter().any(|site| site["symbol"] == name), "{name}");
    }
    assert!(!sites.iter().any(|site| site["symbol"] == "\\bot"));
    let names = notation["symbols"].as_array().unwrap();
    assert!(!names.iter().any(|symbol| symbol["name"] == "z"));
    let alpha = names
        .iter()
        .find(|symbol| symbol["name"] == "\\alpha_j")
        .unwrap();
    assert_eq!([&alpha["use_count"], &alpha["free_use_count"]], [2, 1]);
    for (name, expected) in [("u_{\\mathbb{F}}", true), ("w_{\\mathbb{F}}", false)] {
        assert_eq!(
            notation["entries"]
                .as_array()
                .unwrap()
                .iter()
                .any(|entry| entry["symbol"] == name),
            expected,
            "{name}"
        );
    }
}
#[test]
fn component_bindings_leave_uses_outside_the_statement_free() {
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
    let notation =
        crate::manuscript::notation::Notation::build(&manuscript, &Walk::of(&manuscript));
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
fn a_symbol_named_in_apposition_carries_that_phrase_as_its_role() {
    let manuscript = assembled(
        "\\documentclass{article}\\begin{document}\\section{Values}\
         At radix $\\beta=2$ a value has a significand.\n\n\
         \\section{Blocks}The byte budget $\\beta\\in\\mathbb N$ fixes the block width.\
         The sum of $x$ is exact. Blocks attach scales $\\alpha_j,\\gamma_j$ to their runs.\
         The total $\\sum_{k=0}^{n}y_k$ reads a relation inside a subscript.\n\n\
         \\section{Depths}The alignment depth $f\\in\\mathbb N$ counts positions. With depth $f=3$ the\
         grid is coarse. The absorption inequality $2^{f}<y$ is a use.\\end{document}",
    );
    let notation =
        crate::manuscript::notation::Notation::build(&manuscript, &Walk::of(&manuscript));
    let roles = |symbol: &str| -> Vec<String> {
        notation["sites"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|site| site["symbol"] == symbol && site["meaning"] != "")
            .map(|site| site["meaning"].as_str().unwrap().to_string())
            .collect()
    };
    assert_eq!(roles("\\beta"), ["radix", "byte budget"]);
    for name in ["x", "\\alpha_j", "y_k", "y"] {
        assert!(roles(name).is_empty(), "{name}");
    }
    let depth = roles("f");
    assert!(
        depth.len() == 2 && depth[0] == depth[1],
        "one meaning, reminded: {depth:?}"
    );
    assert_eq!(symbols::named("x_{"), ["x_{}"]);
}
