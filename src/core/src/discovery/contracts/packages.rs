use std::collections::BTreeSet;

#[derive(Debug, Default)]
pub struct Packages {
    pub(crate) directories: BTreeSet<String>,
    pub(crate) root_package: Option<String>,
}
