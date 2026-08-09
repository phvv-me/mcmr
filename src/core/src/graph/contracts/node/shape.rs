/// What one declaration writes around itself, as the frontend read it off its own grammar.
#[derive(Default)]
pub struct NodeShape {
    pub annotation: Option<String>,
    pub return_annotation: Option<String>,
    pub decorators: Vec<String>,
    pub asynchronous: bool,
}
