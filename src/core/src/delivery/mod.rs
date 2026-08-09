use super::runtime::FACT_BATCH_SIZE;
use std::collections::{BTreeMap, BTreeSet};

mod capture;
mod delivered;

pub(super) use capture::{CaptureSelection, GenericCapture};
pub(super) use delivered::Delivered;

/// Route extracted facts either into retained joins or directly to one consumer.
///
/// The pending batches, the deferred typed markers and the record of what was already emitted only
/// agree with one another while facts are still arriving, so nothing here is readable from outside.
/// Closing the delivery is what settles all three at once and hands over what was kept.
pub(super) struct Delivery<'a, Emit>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    retained: BTreeMap<String, Vec<serde_json::Value>>,
    pending: BTreeMap<String, Vec<serde_json::Value>>,
    typed_markers: BTreeSet<String>,
    emitted_families: BTreeSet<String>,
    emitted_count: usize,
    generic: GenericCapture,
    emit: &'a mut Emit,
}

impl<'a, Emit> Delivery<'a, Emit>
where
    Emit: FnMut(String, Vec<serde_json::Value>) -> Result<(), String>,
{
    /// Open one delivery that joins the named families in memory and streams every other one.
    pub(super) fn new(retained: &[String], generic: GenericCapture, emit: &'a mut Emit) -> Self {
        Self {
            retained: retained
                .iter()
                .map(|family| (family.clone(), Vec::new()))
                .collect(),
            pending: BTreeMap::new(),
            typed_markers: BTreeSet::new(),
            emitted_families: BTreeSet::new(),
            emitted_count: 0,
            generic,
            emit,
        }
    }

    /// Close the delivery and hand over everything it kept.
    ///
    /// Marking the generic families nobody produced, draining what is still pending and answering
    /// for every requested family that produced nothing all belong to the same closing moment, so
    /// they run here in that order rather than being three calls a caller could reorder.
    pub(super) fn close(mut self, requested: &[String]) -> Result<Delivered, String> {
        for family in self.generic.unseen() {
            self.generic.marked.insert(family.clone());
            self.generic.rows.entry(family.clone()).or_default();
            (self.emit)(format!("@typed:{family}"), Vec::new())?;
        }
        self.flush()?;
        for family in requested {
            if !self.emitted_families.contains(family) {
                (self.emit)(family.clone(), Vec::new())?;
            }
        }
        Ok(Delivered {
            retained: self.retained,
            generic: self.generic.rows,
        })
    }

    pub(super) fn fact_count(&self) -> usize {
        self.emitted_count + self.retained.values().map(Vec::len).sum::<usize>()
    }

    pub(super) fn mark_typed(&mut self, family: &str, row_count: usize) -> Result<(), String> {
        if row_count >= FACT_BATCH_SIZE {
            (self.emit)(format!("@typed:{family}"), Vec::new())
        } else {
            self.typed_markers.insert(family.to_string());
            Ok(())
        }
    }

    pub(super) fn send(
        &mut self,
        family: String,
        mut produced: Vec<serde_json::Value>,
    ) -> Result<(), String> {
        let capture = self.generic.accept(&family, &mut produced);
        if capture.newly_marked {
            (self.emit)(format!("@typed:{family}"), Vec::new())?;
        }
        if capture.captured && !capture.mirrored {
            self.emitted_count += capture.row_count;
            self.emitted_families.insert(family);
            return Ok(());
        }
        if let Some(stream) = self.retained.get_mut(&family) {
            stream.append(&mut produced);
        } else if !produced.is_empty() {
            self.emitted_count += produced.len();
            self.emitted_families.insert(family.clone());
            let mut ready = Vec::new();
            {
                let pending = self.pending.entry(family.clone()).or_default();
                pending.append(&mut produced);
                while pending.len() >= FACT_BATCH_SIZE {
                    let remainder = pending.split_off(FACT_BATCH_SIZE);
                    ready.push(std::mem::replace(pending, remainder));
                }
            }
            for batch in ready {
                (self.emit)(family.clone(), batch)?;
            }
        }
        Ok(())
    }

    pub(super) fn send_all(
        &mut self,
        held: BTreeMap<String, Vec<serde_json::Value>>,
    ) -> Result<(), String> {
        for (family, produced) in held {
            self.send(family, produced)?;
        }
        Ok(())
    }

    /// Emit every deferred typed marker and every batch that never reached full size.
    fn flush(&mut self) -> Result<(), String> {
        let mut pending = std::mem::take(&mut self.pending);
        let families = pending
            .keys()
            .chain(self.typed_markers.iter())
            .cloned()
            .collect::<BTreeSet<_>>();
        for family in families {
            if self.typed_markers.remove(&family) {
                (self.emit)(format!("@typed:{family}"), Vec::new())?;
            }
            let facts = pending.remove(&family).unwrap_or_default();
            if !facts.is_empty() {
                (self.emit)(family, facts)?;
            }
        }
        Ok(())
    }
}
