---
title: "What gets published"
description: "Fact datasets, the shared rulebook flow, assertions, run instances, and the typed properties a reader filters by."
---

A `mcmr check --writeback` publishes six kinds of entity, and every one of them is derived from
the report the run already produced, nothing is analyzed a second time to state it.

## Fact datasets and one extraction flow per repository

One dataset per fact table your run materialized carries `schemaMetadata` flattened from the
Pydantic fact model as dotted field paths, and a `datasetProfile` stating the rows this run read.
One `DataFlow` names the repository and holds its extraction `DataJob`, which outputs every fact
dataset the run built. That is a lineage graph for source code, published into the place a data
team already reads lineage for everything else.

## One rulebook flow, shared by every codebase

A rule is one thing, so it is one entity, published once as a `DataJob` under a single canonical
`mcmr/rulebook` flow for the whole DataHub instance, rather than copied under each repository that
runs it. Publishing a repository reads what earlier repositories already wrote onto that job and
merges into it, so a rule's `inputDatasets` become the union of every codebase's fact tables for
the families it reads. Two repositories publishing at the same moment race, and the later write
wins.

The merge also carries what each codebase currently reports, `lastResult.<repo>`,
`findings.<repo>`, `lastRun.<repo>`, `since.<repo>`, and `anchor.<repo>`, beside `reposFailing`,
`reposPassing`, and `totalFindings` rollups recomputed from the merged set. A reader following
lineage lands on the rule and reads what it concluded everywhere without opening anything else,
and one link per codebase, failing repositories first, points at the fact table its verdicts are
recorded against.

## Assertions, the timeline a verdict actually lives on

Each rule and subject pair a run judges becomes one DataHub custom assertion, DataHub's own model
for a check an external tool owns. The assertion identity is derived from the rule identifier and
what the verdict is about, so a later run lands on the same assertion instead of creating a
second one, and each run reports one result against it with the record's own fields as properties.

## The run itself, as one process instance

An assertion timeline answers what one rule keeps concluding, it cannot answer what a single
invocation did, every verdict in it belongs to a different rule and a different day. Each
`mcmr check --writeback` mints one run identity, `mcmr-<repository>-<epoch millis>`, stamps it on
every assertion result it reports as `runId`, and writes that same identity as one
`DataProcessInstance` under the repository's flow, carrying a `STARTED` and a `COMPLETE` event,
the second stating `SUCCESS` or `FAILURE` from whether the run had failures.

Its properties say how much the run reached, `files`, `facts`, `failures`, `findings`,
`rulesExecuted`, `rulesFailing`, one `rules<Lane>` count per lane the run activated,
`durationMillis`, and, when the contextual lane ran, the backend, the model, and the run's total
token usage. Reusing the identity already stamped on every verdict is what lets a reader pivot
from one rule's timeline to the invocation that wrote it and back.

## Typed properties and tags a reader actually filters by

| Property | Entity | States |
|---|---|---|
| `lane` | rule job | deterministic, contextual, or external |
| `ruleFamily` | rule job | the family a rule belongs to |
| `codebase` | dataset, flow, job | the repository whose run published this entity |
| `findings` | rule job | how many places a rule currently reports, across every codebase |
| `tokensSpent` | rule job | what every recorded run of a rule has cost its backend |
| `flapScore` | dataset | how often the noisiest subject in a fact table changed verdict lately |

A custom property left as a bare string is a fact nobody can sort or filter. Declaring it once as
a structured property makes it a typed facet every codebase shares, so a reader can ask the
catalog for every contextual rule, or every table that keeps flapping, without knowing which
repository wrote the value. A rule also carries its lane as a colored tag and its family as a
glossary term under one `MCMR Rule Families` group, and only the lanes and families a run actually
reached are published, so no tag exists that nothing carries.

See [Cost provenance](/mcmr/docs/datahub/cost-provenance/) for what `tokensSpent` is built from,
and [Incidents and contracts](/mcmr/docs/datahub/incidents-and-contracts/) for `flapScore` and the
data quality contract a fact table receives.
