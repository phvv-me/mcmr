use serde::{Deserialize, Serialize};

/// One item held by a literal mapping expression, either a stated key or an unpacking.
///
/// An unpacked item carries no key, and dropping it here would let a reader of these facts
/// mistake `{**defaults, "name": name}` for a mapping that states only `name`.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct MappingEntry<T> {
    pub key: String,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub is_spread: bool,
    pub value: T,
}
