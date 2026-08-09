use crate::runtime::TypedRows;

/// Declare the typed fact families a document extraction can be asked for.
///
/// The list is stated once because the flags a selection carries and the typed rows they are read
/// from have to agree name for name, so adding a family stays a single edit.
macro_rules! selected_families {
    ($($family:ident),+ $(,)?) => {
        /// Typed fact families selected for one document extraction.
        #[derive(Clone, Copy)]
        pub(in crate::pipeline::documents) struct SelectedFamilies {
            $(pub(in crate::pipeline::documents) $family: bool,)+
        }

        impl SelectedFamilies {
            /// Read which families the caller left an output buffer for.
            pub(in crate::pipeline::documents) fn of(typed: &TypedRows<'_>) -> Self {
                Self {
                    $($family: typed.families.$family.is_some(),)+
                }
            }
        }
    };
}

selected_families!(
    functions,
    calls,
    classes,
    import_bindings,
    syntax,
    attribute_accesses,
    string_expressions,
);
