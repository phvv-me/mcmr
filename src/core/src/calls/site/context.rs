use serde::{Deserialize, Serialize};

/// Conditions surrounding one invocation that do not identify its target or syntax.
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub(crate) struct CallContext {
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) result_is_discarded: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_shadowed: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) has_ambiguous_alias: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_decorator_factory: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) has_starred_arguments: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) enclosing_is_async: bool,
}
