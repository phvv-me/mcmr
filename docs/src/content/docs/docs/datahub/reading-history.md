---
title: "Read history back"
description: "Inspect earlier verdicts before changing a governed subject."
---

`mcmr history` reads the assertion timelines produced by writeback. It reports whether each subject
is passing or failing, when that state began, how many repairs landed, and why it last failed.

```sh
mcmr history .
mcmr history . --select "ALL-DUPL*"
mcmr history . --assets "urn:li:dataset:(urn:li:dataPlatform:snowflake,orders,PROD)"
```

`--select` narrows rules when MCMR discovers subjects from the repository. Repeating `--assets`
names governed identities directly and skips that analysis.

## Where a verdict lives

A rule about a governed DataHub asset anchors its assertion on that asset. Other rules anchor on
the fact dataset for the first table in their signature. File and fact identity remain properties
of the assertion result.

## How stale failures close

When a rule runs and no longer reports a prior file, writeback adds one passing event that states
the old finding is no longer present. A rule that did not execute closes nothing. This distinction
prevents skipped work from looking like a repair.

History is the low-cost first step for an agent working on an established repository. It can avoid
repeating analysis and reopening a rejected change. See
[Institutional memory](/mcmr/docs/concepts/institutional-memory/) for the operating model.
