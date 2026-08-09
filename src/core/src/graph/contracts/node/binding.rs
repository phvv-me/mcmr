use super::super::parameter_kind::ParameterKind;

/// How one parameter binds at a call site, which every frontend states from its own grammar.
pub struct NodeBinding {
    pub ordinal: usize,
    pub kind: ParameterKind,
    pub has_default: bool,
}
