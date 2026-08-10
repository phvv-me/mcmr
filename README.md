<div align="center">

[![My Code, My Rules banner](https://raw.githubusercontent.com/phvv-me/mcmr/main/docs/assets/banner.png)](https://phvv.me/mcmr/)

[![CI](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml/badge.svg)](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml)
[![Publish](https://github.com/phvv-me/mcmr/actions/workflows/publish.yml/badge.svg)](https://github.com/phvv-me/mcmr/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/mcmr)](https://pypi.org/project/mcmr/)
[![Python](https://img.shields.io/pypi/pyversions/mcmr)](https://pypi.org/project/mcmr/)
[![Docs](https://img.shields.io/badge/docs-phvv.me%2Fmcmr-C6281C)](https://phvv.me/mcmr/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml)

</div>

> **Warning** MCMR is early `0.0.x` software. Its rules and command line may still change.

## Installation

MCMR requires Git and Python 3.14 or newer. Use standard CPython for the simple PyPI install.

```sh
pip install mcmr
mcmr check .
```

Use `uv tool install mcmr` for an isolated command line installation.

MCMR also runs on free-threaded Python `3.14t+`. Polars does not yet publish a compatible PyPI
runtime wheel, so use the source environment described in the
[install guide](https://phvv.me/mcmr/docs/start/install/) for that interpreter.

## What it is

MCMR is a policy engine for whole repositories. A Rust kernel reads source once into typed fact
tables. Python rules query the shared evidence and report exact findings with source locations.

- Deterministic rules are local, fast, and enabled by default.
- Contextual rules use a configured model only when you enable them.
- External rules can join repository facts with systems such as DataHub.
- Safe repairs are kept only after MCMR reparses the edit and reruns the rule.
- Plugins can add rules and evidence providers through public entry points.

MCMR reads Python, Rust, TypeScript, C, C++, and CUDA.

## Usage

```sh
mcmr check . --format concise
mcmr check . --repair preview
mcmr check . --repair apply
mcmr check . --contextual --external
```

Write every verdict to DataHub, then read the history before the next agent changes the code.

```sh
mcmr check . --external --writeback
mcmr history .
```

## Demo

The repository includes a deliberately messy MCP server. Run every enabled rule without changing
the demo.

```sh
mcmr check demo/ --contextual --external --writeback --report-only
```

See the [documentation](https://phvv.me/mcmr/docs/), the
[rule reference](https://phvv.me/mcmr/docs/rules/), and the
[recorded DataHub examples](examples/datahub). [SYSTEM.md](SYSTEM.md) documents the architecture.
The docs also cover [contextual setup](https://phvv.me/mcmr/docs/start/contextual-rules/) and
[rule controls](https://phvv.me/mcmr/docs/reference/rule-control/).

MCMR is licensed under Apache 2.0.
