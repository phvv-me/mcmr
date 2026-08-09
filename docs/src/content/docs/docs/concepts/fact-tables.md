---
title: "Fact tables"
description: "What the Rust kernel extracts, and why rules query shared tables instead of looping over objects."
---

A `Fact` is one independently identifiable unit of evidence, a function signature, a call, an
import binding, a test case. Fact models define the provider's schema and its legal value domain,
and constrained types make impossible counts, percentages, paths, and identities fail at the
provider boundary rather than downstream in a rule.

Production queries do not loop over Pydantic objects. The kernel normalizes facts into typed
Polars relations, and `Table[FunctionFact]`, `Table[CallFact]`, and every other table type expose
those relations without hiding the collection or the joins underneath them.

## 63 typed families, seven categories

MCMR currently declares 63 fact table families across seven categories, grouped by the directory
the fact models already live in rather than by a second taxonomy someone has to keep in sync.

| Category | What it holds |
|---|---|
| structure | How a repository is arranged, directories, classes, calls, CI |
| program | What the program does, modules, functions, exceptions, lineage |
| project | The project around the code, configuration, history, prose, risk |
| symbols | The names a codebase declares, exports, overrides, reaches, and types |
| testing | The test suite, cases, fixtures, waivers, quarantined tests |
| languages | What one language contributes that no other has to answer for |
| foundation | What every other family is built out of, spans, evidence, graphs |

## How a rule reads a table

The first table in a rule's signature supplies output identities, the row a finding is about.
Additional tables provide joinable evidence. Language annotations can narrow any table before the
rule runs, so a Python-only rule never pays for a Rust row it will never match.

```python
@rule("PY-IMPO0003", fix_safety=FixSafety.REVIEW)
def unused_import(subject: Table[ImportBindingFact]) -> OccurrenceQuery:
    frame = subject.facts()
    value = (pl.col("reference_count") == 0) & ~pl.col("is_reexported")
    return RuleQuery.boolean(
        frame,
        value,
        findings=FindingQuery.precise_boolean(frame, value, "unused import"),
    )
```

Rules derive conclusions from primitive columns. A provider may retain a call target, a source
span, a reference count, or a graph edge, but never a field like `should_move` that already
answers the rule. That judgment stays with the rule and its declared policy.

## Where a table can come from

Most families come from the Rust kernel walking your source tree once. Others come from an
external provider, DataHub's data asset facts, for one, that declares ownership of a family
through the `mcmr.providers` entry point.

```python
from mcmr.facts import DataAssetFact, Fact
from mcmr.plugins import ProviderContext, RepositoryTables, provider


@provider
class DataHubProvider:
    families = {DataAssetFact: set()}

    async def tables(self, context: ProviderContext) -> RepositoryTables:
        ...
```

Provider ownership is exact. Two providers cannot claim the same family, and a provider must
return every requested family it owns and no others. Native table dependencies are materialized
once and reused if a rule also reads them directly, and a fact class that sets `external_evidence`
keeps its rules out of an ordinary offline run until `--external` asks for them.

See [Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for what a rule does with a table once
it has one, and [Why metadata](/mcmr/docs/datahub/why-metadata/) for how every published fact
table becomes a dataset DataHub can show lineage for.
