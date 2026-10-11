use super::{CorpusFile, Manuscript, Walk};

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
    assert_eq!((found.len(), found[0].language.as_str()), (1, "typst"));
    let walk = Walk::of(&found[0]);
    assert_eq!(walk.sections.len(), 3);
    assert_eq!(
        [
            &walk.sections[0]["title"],
            &walk.labels[0]["name"],
            &walk.labels[1]["kind"]
        ],
        ["Setup", "setup", "equation"]
    );
    assert_eq!(
        crate::manuscript::typst::named("bb(A)_k + alpha"),
        vec!["bb(A)_k", "alpha"]
    );
}
#[test]
fn typst_refuses_runtime_transformations() {
    let dynamic = crate::manuscript::typst::TypstReader::read(&CorpusFile {
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
    assert_eq!((found.len(), Walk::of(&found[0]).sections.len()), (1, 1));
    assert_eq!(Walk::of(&found[0]).sections[0]["title"], "Visible");
    for (binding, call) in [("style", "style"), ("style as text", "text")] {
        std::fs::write(
            &paper,
            format!("#import \"../template.typ\": {binding}\n#{call}[Content]\n"),
        )
        .unwrap();
        assert!(
            Manuscript::scan(root.path(), &scope)
                .err()
                .expect("an imported custom call needs evaluation")
                .contains(&format!("call to `{call}`"))
        );
    }
}
#[test]
fn typst_import_resolution_refuses_missing_paths_and_cycles() {
    let root = tempfile::tempdir().expect("a temporary manuscript opens");
    std::fs::create_dir(root.path().join("chapters")).unwrap();
    let paper = root.path().join("chapters/paper.typ");
    let scope = crate::discovery::Scope::of(root.path(), &[".typ".to_string()]);
    for (template, source, error) in [
        (
            "#let value = 1\n",
            "#import \"template.typ\": value\n= Visible\n",
            "unresolved Typst import",
        ),
        (
            "#import \"chapters/paper.typ\"\n#let value = 1\n",
            "#import \"../template.typ\": value\n= Visible\n",
            "cyclic Typst",
        ),
        (
            "#let value = 1\n",
            "#let target = \"../template.typ\"\n#import target: value\n",
            "unresolved Typst",
        ),
    ] {
        std::fs::write(root.path().join("template.typ"), template).unwrap();
        std::fs::write(&paper, source).unwrap();
        assert!(
            Manuscript::scan(root.path(), &scope)
                .err()
                .expect("invalid imports must fail")
                .contains(error),
            "{source}"
        );
    }
}
