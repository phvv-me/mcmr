/// Where in the assembled manuscript one element sits.
///
/// Reading order is the whole point of this family, so every element carries its own index in the
/// flattened stream beside the section, statement and float that were open when it was met. A
/// rule then compares two orders rather than two spans, which is what makes a reference that
/// points backwards distinguishable from one that points forwards.
#[derive(Debug, Clone, Copy)]
pub struct Position {
    pub order: usize,
    pub section: Option<usize>,
    pub statement: Option<usize>,
    pub float: Option<usize>,
    pub in_body: bool,
    pub in_cells: bool,
    pub in_math: bool,
    pub in_proof: bool,
}

impl Position {
    /// The position an element outside every enclosing construct sits at.
    pub fn opening() -> Self {
        Self {
            order: 0,
            section: None,
            statement: None,
            float: None,
            in_body: false,
            in_cells: false,
            in_math: false,
            in_proof: false,
        }
    }
}
