---
title: "What gets published"
description: "The DataHub entities produced by one writeback run."
---

Writeback derives every entity from the completed report. It never runs the analysis twice.

## Fact datasets and extraction lineage

Each materialized fact table becomes a dataset with schema metadata and a row profile. One
repository flow owns an extraction job that outputs those datasets. The result is lineage from a
codebase to the facts its rules queried.

## A shared rulebook

Each rule becomes one job under the canonical `mcmr/rulebook` flow. The job collects input datasets
from every repository that runs it. Structured properties retain the latest result, finding count,
anchor, and update time per repository, plus cross-repository totals.

## Assertion timelines

Every rule and subject pair becomes one custom assertion. Its stable identity lets later runs add
results to the same timeline. File and fact identity stay on each result, so one rule can fail in
two places without collapsing them together.

## Run instances

Each invocation becomes one process instance with start and completion events. It records file,
fact, rule, failure, finding, duration, and lane counts. Contextual runs also record backend, model,
and tokens.

## Catalog structure

Rules receive lane tags and family glossary terms. Fact tables receive structured properties such
as codebase and flap score. Only values reached by a run are published.

Repository-wide rule verdicts can also become DataHub contract clauses. Repeated state changes can
raise or resolve incidents. Those behaviors are explained in
[Incidents and contracts](/mcmr/docs/datahub/incidents-and-contracts/).

See [Cost provenance](/mcmr/docs/datahub/cost-provenance/) for contextual usage and
[Reading history back](/mcmr/docs/datahub/reading-history/) for the read path.
