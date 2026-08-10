---
title: "Fact tables"
description: "How one repository walk becomes shared typed evidence."
---

A fact is one identifiable unit of evidence such as a function, call, import, test, or data asset.
Fact models define the provider schema and legal value domain. Invalid counts, paths, and identities
fail at the provider boundary.

The Rust kernel normalizes facts into Polars relations. Rules query those relations through typed
tables instead of looping over Python objects.

## How rules use tables

The first table in a rule signature supplies output identities. Additional tables provide evidence
that can be joined. Language annotations narrow a table before the rule runs.

```python
@rule("PY-IMPO0003", fix_safety=FixSafety.REVIEW)
def unused_import(subject: Table[ImportBindingFact]) -> OccurrenceQuery:
    frame = subject.facts()
    value = (pl.col("reference_count") == 0) & ~pl.col("is_reexported")
    return RuleQuery.boolean(frame, value)
```

Providers retain primitive columns such as a source span, call target, or reference count. They do
not emit a conclusion such as `should_move`. The rule owns that judgment and its policy.

## Where facts come from

Most facts come from the kernel. External plugins can own other families through the
`mcmr.providers` entry point. DataHub supplies governed data assets this way.

Provider ownership is exact. Two providers cannot claim the same family. A provider must return
every requested family it owns and no other family. Native tables are extracted once and reused.

See [Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for how the engine schedules rules.
