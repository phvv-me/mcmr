use self::families::SelectedFamilies;
use crate::runtime::{LegacyRetention, TypedRows};

mod families;

/// Typed families one document extraction must retain.
#[derive(Clone, Copy)]
pub(super) struct ExtractionSelection {
    pub(in crate::pipeline::documents) families: SelectedFamilies,
    pub(in crate::pipeline::documents) retention: LegacyRetention,
}

impl ExtractionSelection {
    pub(super) fn of(typed: &TypedRows<'_>) -> Self {
        Self {
            families: SelectedFamilies::of(typed),
            retention: typed.retention,
        }
    }
}
