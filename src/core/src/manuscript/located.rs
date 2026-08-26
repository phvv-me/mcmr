use super::element::Element;

/// One element and the exact place a reader would find it.
///
/// A manuscript is assembled from many files, so the path travels with every element rather than
/// with the file it came from. That is what lets one flattened reading order carry findings back
/// to the section file that actually holds the defect.
#[derive(Debug, Clone)]
pub struct Located {
    pub element: Element,
    pub path: String,
    pub line: usize,
}

impl Located {
    pub fn new(element: Element, path: &str, line: usize) -> Self {
        Self {
            element,
            path: path.to_string(),
            line,
        }
    }
}
