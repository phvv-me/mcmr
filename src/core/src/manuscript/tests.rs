mod reader;
mod semantics;
mod typst;

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
