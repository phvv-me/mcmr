use super::super::runtime::FACT_BATCH_SIZE;
use std::io::{BufRead, BufReader, BufWriter, Seek, Write};

/// One family's spooled facts, which reading consumes so no family can be read twice.
pub(crate) struct Spool {
    family: String,
    file: BufWriter<std::fs::File>,
}

impl Spool {
    /// Open one empty spool for a family, outside memory.
    pub(super) fn open(family: String) -> Result<Self, String> {
        tempfile::tempfile()
            .map(|file| Self {
                family,
                file: BufWriter::with_capacity(1024 * 1024, file),
            })
            .map_err(|failure| format!("a fact spool could not be opened: {failure}"))
    }

    /// Drain this family in bounded batches rather than rebuilding it in memory.
    pub(crate) fn drain<Visit>(self, mut visit: Visit) -> Result<(), String>
    where
        Visit: FnMut(Vec<serde_json::Value>) -> Result<(), String>,
    {
        let mut batch = Vec::with_capacity(FACT_BATCH_SIZE);
        for fact in self.facts()? {
            batch.push(fact?);
            if batch.len() == FACT_BATCH_SIZE {
                visit(std::mem::take(&mut batch))?;
            }
        }
        if !batch.is_empty() {
            visit(batch)?;
        }
        Ok(())
    }

    /// Read this family whole, for the joins that need every fact at once.
    pub(crate) fn read(self) -> Result<Vec<serde_json::Value>, String> {
        self.facts()?.collect()
    }

    /// Append facts to what this family has already spooled.
    pub(super) fn write(&mut self, facts: Vec<serde_json::Value>) -> Result<(), String> {
        let family = &self.family;
        for fact in facts {
            serde_json::to_writer(&mut self.file, &fact)
                .map_err(|failure| format!("a {family} fact could not be spooled: {failure}"))?;
            writeln!(self.file)
                .map_err(|failure| format!("a {family} fact could not be spooled: {failure}"))?;
        }
        Ok(())
    }

    /// Rewind the written file and hand back every fact it holds, one parsed line at a time.
    fn facts(self) -> Result<impl Iterator<Item = Result<serde_json::Value, String>>, String> {
        let family = self.family;
        let mut file = self.file.into_inner().map_err(|failure| {
            format!("the {family} fact spool could not be flushed: {failure}")
        })?;
        file.rewind().map_err(|failure| {
            format!("the {family} fact spool could not be rewound: {failure}")
        })?;
        Ok(BufReader::new(file).lines().map(move |line| {
            let line =
                line.map_err(|failure| format!("the {family} fact spool failed: {failure}"))?;
            serde_json::from_str(&line)
                .map_err(|failure| format!("a spooled {family} fact is invalid: {failure}"))
        }))
    }
}
