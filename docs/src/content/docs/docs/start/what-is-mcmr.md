---
title: "What MCMR is"
description: "A fast code policy engine that reads a repository once and reports precise, cited findings."
---

MCMR is a fast code policy engine for whole repositories. A Rust kernel understands the source
tree once. Typed Python rules then query shared Polars tables and report precise findings. Rules
can also offer verified fixes.

MCMR currently reads Python, Rust, TypeScript, C, C++, and CUDA. Deterministic checks are local
and stateless. Contextual checks and network providers are explicit opt-ins, off by default.

## The shape of a run

Six properties hold on every run, and none of them are negotiable.

- One repository walk supplies one request.
- One selected fact family is extracted once.
- One rule is invoked once, and it receives only the tables and services its own signature names.
- Providers retain primitive evidence and never decide a rule's verdict.
- A normal run is stateless. It writes nothing unless you ask for a report or a repair.
- A fix is kept only after syntax validation and a fresh rule check confirms it worked.

That last property is the one most linters skip. Most tools either never offer a fix or trust the
fix they generated. MCMR writes the candidate, reparses it, reruns the exact rule that found the
problem, and only keeps the edit if that rule now passes.

## Why it reads differently from a linter

A traditional linter walks the tree once per rule, or once per file per rule. MCMR's kernel
extracts each fact family, a function signature, a call, an import binding, a test case, exactly
once, and every rule that needs that family queries the same in-memory table. Two hundred rules
reading `FunctionFact` cost one extraction, not two hundred.

A finding also has to earn its place. Every rule states a summary, a definition, the evidence it
reads, the exceptions it makes, and the references it draws on, checked by the catalog itself
rather than left to trust. A finding names an exact source span and states the measurement behind
it, so a result reads as a citation rather than an opinion.

## Rules, plugins, and the DataHub integration

A rule package publishes an `mcmr.rules` entry point. An external data integration publishes an
`mcmr.providers` entry point. Installed packages add rules and fact providers without editing
MCMR itself.

```toml
[project.entry-points."mcmr.rules"]
acme = "acme_mcmr.rules"

[project.entry-points."mcmr.providers"]
acme = "acme_mcmr.provider:AcmeProvider"
```

The bundled DataHub integration ships the same way, as the `mcmr_datahub` plugin under `src/mcmr_datahub`
in the MCMR repository itself, registered through those same two entry points rather than through
a private path. It is the worked example to read before writing your own. See
[Why metadata](/mcmr/docs/datahub/why-metadata/) for what it adds once you turn it on.

## Where to go next

[Install](/mcmr/docs/start/install/) gets the CLI running against your own repository in a couple
of commands. [The demo walkthrough](/mcmr/docs/start/demo-walkthrough/) shows fifty failures
collapse to four across three thematic patches, entirely offline. [Fact tables](/mcmr/docs/concepts/fact-tables/)
and [Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) explain the two ideas everything else
in MCMR is built from.
