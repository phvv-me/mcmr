---
title: "CLI commands"
description: "Choose the command that matches the work you need to do."
---

`mcmr --help` and `mcmr <command> --help` are the exact reference. This page is the short map.

## Check and repair

`mcmr check [ROOT]` runs selected rules. Common options include `--select`, `--format`, `--limit`,
`--output`, `--report-only`, and `--kernel`.

Execution flags turn lanes on or off. They include `--deterministic`, `--contextual`, and
`--external`. `--writeback` records verdicts. `--repair preview` shows fixes while `--repair apply`
keeps verified safe fixes. `--maximum-fixes` limits a repair run.

`mcmr history [ROOT]` reads prior DataHub verdicts. Use `--select` for rules or repeat `--assets`
for direct governed identities.

`mcmr demo` runs the recorded DataHub example without a live service.

`mcmr backends [ROOT]` shows the contextual backend that a normal check would use.

## Explore the rulebook

- `mcmr catalog` exports the typed rule catalog as JSON.
- `mcmr coverage` maps upstream rules to MCMR support.
- `mcmr replacement` audits frozen legacy capabilities.
- `mcmr influence` ranks the sources cited by rules.

## Evaluate contextual models

`mcmr model-sweep [ROOT]` runs contextual rules through a chosen backend and model.

`mcmr contextual-experiment LABELS [ROOT]` compares model profiles against reviewed labels.

## Inspect repository structure

- `mcmr diagram` draws package or class structure.
- `mcmr graph` lists declaration reachability.
- `mcmr matrix` projects imports as a design structure matrix.
- `mcmr impact --changed PATHS` finds affected modules.
- `mcmr simulate` evaluates import changes without editing files.

`mcmr floor` measures the table planner baseline without repository input.

Commands that accept `[ROOT]` default to the current directory.
