---
title: "Install"
description: "Get the mcmr CLI running against your own repository."
---

MCMR ships as one Python distribution built from a Rust extension and requires Python 3.14 or
newer. Its primary runtime target is free-threaded Python `3.14t+`, and standard CPython `3.14+`
is supported too. Releases include Linux wheels for CPython 3.14 and `3.14t`. MCMR itself is
developed and rehearsed on `3.14t` with the GIL disabled. An installer may build dependencies
from source when their projects do not publish free-threaded wheels yet. Install the command line
application from PyPI.

```sh
pip install mcmr
mcmr check .
```

Use `uv tool install mcmr` for an isolated command line installation.

`mcmr check .` runs every deterministic rule that applies to the languages your repository
contains, prints a Rich report to the terminal, and exits nonzero if anything failed. Nothing is
written to disk. A first run on an unfamiliar codebase is usually loud, and that is expected,
narrow it before you tune it.

## Narrow a first run

```sh
mcmr check . --select "PY-*" --limit 20
mcmr check . --format concise
```

`--select` filters by rule identifier or callable substring. `--format concise` collapses each
finding to one line, which is the fastest way to see the shape of a large report before deciding
what to fix first. [CLI commands](/mcmr/docs/reference/cli/) documents every flag `check` accepts.

## Turn on more than the deterministic lane

Contextual rules ask a configured classification backend to judge something a Boolean or a count
cannot answer, and external rules read live evidence from a system outside the repository. Both
stay off until you ask for them, because both cost something a purely local check does not.

```sh
mcmr check . --contextual
mcmr check . --external
```

`mcmr backends` shows which contextual backend an ordinary check would use, without starting it,
which is worth running once before your first `--contextual` check.

```toml
[tool.mcmr.contextual]
backend = "codex"
model = "gpt-5.6-terra"
reasoning_effort = "medium"
```

## Preview and apply repairs

A rule that can offer a fix says so once, on its own declaration, as either `safe` or `review`.
`--repair preview` never writes a file. `--repair apply` writes only the fixes a rule declared
safe, and MCMR reparses the result and reruns the originating rule before it keeps the edit.

```sh
mcmr check . --repair preview
mcmr check . --repair apply
```

See [Verified repairs](/mcmr/docs/concepts/verified-repairs/) for what separates a `safe` fix from
a `review` one, and why a directory move needs a stricter proof than a source edit.

## Working on MCMR itself

Contributing to the MCMR repository, rather than running it against your own code, uses
[chefe](https://github.com/phvv-me/chefe) to own the Python, Rust, and Node environments together.

```sh
chefe install
chefe run setup
chefe run lint
chefe run typecheck
chefe run test
chefe run contribute
```

`chefe run contribute` is the same gate CI runs, lint, typecheck, the Python suite, and the Rust
kernel's own clippy and cargo tests, so it is the one command worth running before opening a pull
request.

## Try the repository demo

```sh
git clone https://github.com/phvv-me/mcmr.git
cd mcmr
mcmr demo
```

The demo lives in the source repository. It runs the complete DataHub workflow, repair included,
over a recorded catalog with no running service and no network access. [The demo
walkthrough](/mcmr/docs/start/demo-walkthrough/) narrates what it does and why.
