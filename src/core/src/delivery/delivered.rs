use std::collections::BTreeMap;

/// What one closed delivery kept once nothing more can be sent to it.
pub(crate) struct Delivered {
    pub(crate) retained: BTreeMap<String, Vec<serde_json::Value>>,
    pub(crate) generic: BTreeMap<String, Vec<serde_json::Value>>,
}
