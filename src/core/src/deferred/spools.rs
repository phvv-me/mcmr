use super::spool::Spool;
use std::collections::BTreeMap;

/// Keep deferred fact streams outside memory until the join that consumes each one.
pub(crate) struct FactSpools {
    files: BTreeMap<String, Spool>,
}

impl FactSpools {
    pub(crate) fn new(families: impl IntoIterator<Item = String>) -> Result<Self, String> {
        #[cfg(test)]
        super::FORBID_FACT_SPOOLS.with(|forbidden| {
            assert!(
                !forbidden.get(),
                "the native analysis session must not open a compatibility fact spool"
            );
        });
        let files = families
            .into_iter()
            .map(|family| Spool::open(family.clone()).map(|spool| (family, spool)))
            .collect::<Result<_, _>>()?;
        Ok(Self { files })
    }

    pub(super) fn holds(&self, family: &str) -> bool {
        self.files.contains_key(family)
    }

    /// Hand one family's spool over, which is the only way to read it and so happens once.
    pub(crate) fn take(&mut self, family: &str) -> Result<Spool, String> {
        self.files
            .remove(family)
            .ok_or_else(|| format!("no fact spool was opened for {family}"))
    }

    pub(crate) fn write(
        &mut self,
        family: &str,
        facts: Vec<serde_json::Value>,
    ) -> Result<(), String> {
        self.files
            .get_mut(family)
            .ok_or_else(|| format!("no fact spool was opened for {family}"))?
            .write(facts)
    }
}
