use serde::{Deserialize, Serialize};

/// The resolved identity and provenance of one invocation target.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct CallTarget {
    pub(crate) qualified_name: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub(crate) target_id: String,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_external: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_standard_library: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_first_party: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub(crate) is_constructor: bool,
}
