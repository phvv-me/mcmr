/// Where one declaration was written, and the text it was written with.
#[derive(Default)]
pub struct NodePlacement {
    pub path: String,
    pub line: Option<usize>,
    pub source: Option<String>,
}
