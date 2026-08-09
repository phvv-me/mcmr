---
title: "Institutional memory"
description: "What the next agent reads before it changes your code, so it never rediscovers what a previous run already knew."
---

An agent converging a legacy repository usually starts from nothing. It re-derives which rule has
been failing, guesses whether a fix was already tried and refused, and spends a batch
rediscovering what a previous run already concluded. MCMR keeps no cache of its own by default,
but when you turn on writeback, it leaves that conclusion somewhere durable, so the next run, or
the next agent, reads it instead of repeating the analysis.

```sh
mcmr check . --external --writeback
mcmr history .
```

`mcmr history` never judges the repository. It reads what earlier runs already concluded about
the governed assets a repository names, and states, per rule, whether it is passing or failing,
since when, how many repairs already landed, and why it last failed.

```text
demo/facts/literal_group_fact
  ALL-DUPL0002  passing since 2026-08-07 12:43
  ALL-DUPL0005  passing since 2026-08-07 12:47  previously `the request envelope
                                                could not be accepted` is
                                                written 4 times in this module
```

## A verdict closes itself, it is never overwritten silently

Nothing writes a file-scoped verdict again once that file is repaired, renamed, or deleted, each
publication reconciles the timeline, so any file a rule no longer reports gets one passing event
stating that it is no longer reported. A rule that did not run closes nothing, silence is not a
resolution, and a rule that ran states every file it still reports.

The clearest example is one rule holding two opposite verdicts about two files at once.

```text
  ALL-COMM0003  failing since 2026-08-07 12:43  `TODO` marks unresolved work
  ALL-COMM0003 mcp/router.py  failing since 2026-08-07 12:56  `TODO` marks unresolved work
  ALL-COMM0003 mcp_tools.py  passing since 2026-08-07 13:07  previously `TODO` marks
                                                              unresolved work
```

`mcp_tools.py` no longer exists after a later stage, so its row closed itself and kept what it
used to say. `mcp/router.py` still carries the marker. Nobody wrote either line by hand, and
rerunning the same tree a second time prints nothing, because there is nothing left to close,
which is how you know the reconciliation is idempotent rather than rewriting history on every
pass.

## Naming an asset directly skips the analysis

```sh
mcmr history . --assets "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.raw.orders,PROD)"
```

Learning which subjects a repository names needs neither a model's opinion nor a network read the
project did not already enable, so `mcmr history` runs neither lane beyond what your configuration
already turned on. Naming the asset directly is the fast path an agent takes once it already knows
what it is about to touch.

## Where this actually lives

Institutional memory is not a separate system, it is what a normal `mcmr check --writeback`
already produces, read back through DataHub, the catalog most data teams already run.
[What gets published](/mcmr/docs/datahub/what-gets-published/) explains the entities a run writes,
and [Reading history back](/mcmr/docs/datahub/reading-history/) goes deeper into what `mcmr
history` reads and how it is grouped.
