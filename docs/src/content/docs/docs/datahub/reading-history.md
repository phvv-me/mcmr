---
title: "Reading history back"
description: "What mcmr history answers before an agent touches a file, and where each verdict is anchored."
---

`mcmr history` is the read side of writeback, and the reason writeback is worth doing at all. It
reads the recorded verdicts for the subjects a repository names and states, per rule, whether it
is passing or failing, since when, how many repairs already landed, and why it last failed,
grouped by the warehouse asset or the fact table each timeline belongs to.

```sh
mcmr history .
mcmr history . --select "ALL-DUPL*"
mcmr history . --assets "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.raw.orders,PROD)"
```

`--select` narrows the analyzed rules by callable when assets are not named directly. `--assets`
is repeatable and skips the analysis entirely, the fast path an agent takes once it already knows
what it is about to touch. Learning which subjects a repository names needs neither a model's
opinion nor a network read your configuration did not already enable, so this command runs neither
lane beyond what you turned on for check.

## Where a verdict is anchored

A rule that names a governed identity, a warehouse table a rule proves is unreferenced by any
pipeline, keeps storing its verdict there, since that asset is a subject somebody else already
owns. Every other rule anchors on the fact dataset published for the first table in its signature.
The verdict's own identity is the file and fact a finding named, so a rule failing at two files
inside one table keeps two timelines under one subject, and the file travels with the verdict as a
property.

```text
demo/facts/call_fact
  PY-CLI0001    failing since 2026-08-07 12:43  `argparse.ArgumentParser` builds a
                                                second CLI schema instead of
                                                exposing typed callables through
                                                Cyclopts
```

## A file-scoped timeline closes on its own

Nothing writes a file-scoped verdict again once that file is repaired, renamed, or deleted. Each
publication reconciles the timeline, so any file a rule no longer reports receives one passing
event stating that it is no longer reported, and a rule that did not run closes nothing, silence
is not a resolution. See [Institutional memory](/mcmr/docs/concepts/institutional-memory/) for the
worked example of one rule holding a passing and a failing verdict about two different files at
the same moment.

## Why this is the fast path, not a nice-to-have

An agent converging a legacy repository that skips this step spends a batch rediscovering a
failure somebody already recorded, or reattempting a repair that was already refused for a
documented reason. Reading history first is strictly cheaper, and it costs nothing beyond the
configuration you already turned on for an ordinary check.
