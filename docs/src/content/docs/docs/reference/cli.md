---
title: "CLI commands"
description: "Every command mcmr --help lists, grouped by what it is for, verified against the CLI itself."
---

`mcmr --help` and `mcmr <command> --help` are the source of truth. This page groups the same
commands by what you would reach for them to do.

## Check and repair

**`mcmr check [ROOT]`** runs the catalog over a repository and judges it against each rule's
effective policy.

| Flag | Does |
|---|---|
| `--select` | Substring that narrows the selected rules by callable |
| `--suffixes` | Comma-separated source suffixes, for a repository in another language |
| `--format` | `rich` for structured detail, `full` for plain diagnostics, `concise` for one line, or `json` |
| `--limit` | How many detailed diagnostics the report shows, default 20 |
| `--repair` | `none`, `preview`, `apply`, or `apply-review` through verified fixpoints |
| `--maximum-fixes` | Bound the number of verified edits one run applies, default 100 |
| `--output` | Optional path that receives the complete JSON report |
| `--report-only` | Report failures without returning a failing process status |
| `--deterministic` / `--contextual` / `--external` | Enable or disable one execution lane |
| `--rule-coverage` | `available` or `all`, fail when any selected rule could not execute |
| `--writeback` / `--no-writeback` | Record this run's verdicts, or suppress a project's own default |
| `--label` | The label each recorded verdict and institutional memory link carries |

`mcmr history [ROOT]` reads what previous runs already concluded, `--select`, `--assets`
(repeatable), and `--kernel`. See [Reading history back](/mcmr/docs/datahub/reading-history/).

`mcmr demo` runs the complete DataHub workflow over a recorded catalog with no running service,
`--example` points at a different recorded workspace than the bundled `examples/datahub`.

`mcmr backends [ROOT]` shows which contextual backend an ordinary check would use, without
starting it.

## Explore the catalog

`mcmr catalog [--output]` exports the live typed rule catalog as JSON.

`mcmr coverage` shows what MCMR does about every rule an inventoried upstream tool ships,
`--tool`, `--group`, `--state` (`native`, `delegated`, `adapted`, `inapplicable`, `unavailable`),
and `--limit`.

`mcmr replacement` audits every frozen legacy rule and capability against its declared successor,
no arguments.

`mcmr influence [--kind] [--limit]` shows which sources shaped MCMR, most referenced first,
`--kind` narrows to book, paper, standard, language, documentation, article, or tool.

## Contextual rules

`mcmr model-sweep [ROOT]` exercises every contextual rule through a configured live backend,
`--backend`, `--model`, `--reasoning-effort` override the project's own configuration for this
stateless sweep alone, `--workers` bounds concurrency, default 8.

`mcmr contextual-experiment LABELS [ROOT]` compares contextual backends against one complete
reviewed label corpus, `--workers`, `--include-sol` adds the slower Sol medium profile after Luna
high, `--output`.

## Understand a repository's structure

`mcmr diagram [ROOT]` draws the classes or the packages of a repository, `--kind` is `class` or
`package`, `--format` is `d2` or `mermaid`.

`mcmr graph [ROOT]` shows how the declarations of a repository reach each other, `--limit` bounds
how many rows each section shows, default 15.

`mcmr matrix [ROOT]` projects the imports of a repository as a design structure matrix,
`--format` `text` or `json`, `--limit` bounds the text grid, default 32.

`mcmr impact --changed PATHS [ROOT]` reports the modules a change to these comma-separated paths
could break, `--format` `text` or `json`.

`mcmr simulate [ROOT]` asks what adding or removing imports would do to the shape of a repository
without editing a file, `--add` and `--remove` take comma-separated `importer:imported` pairs.

## Measurement

`mcmr floor [--samples] [--facts] [--output]` measures the table catalog planner floor without
repository IO, `--samples` bounds repeated measurements, default 9.

Every command that takes `[ROOT]` defaults to `.`, and every command that reads source accepts
`--kernel` to point at an explicit kernel binary instead of the one built from your checkout.
