<div align="center">

[![MCMR banner](https://raw.githubusercontent.com/phvv-me/mcmr/main/docs/assets/banner.png)](https://phvv.me/mcmr/)

[![CI](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml/badge.svg)](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml)
[![Release](https://github.com/phvv-me/mcmr/actions/workflows/publish.yml/badge.svg)](https://github.com/phvv-me/mcmr/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/mcmr)](https://pypi.org/project/mcmr/)
[![Python](https://img.shields.io/pypi/pyversions/mcmr)](https://pypi.org/project/mcmr/)
[![Docs](https://img.shields.io/badge/docs-phvv.me%2Fmcmr-blue)](https://phvv.me/mcmr/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/phvv-me/mcmr/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/phvv-me/mcmr)](LICENSE)

</div>

> [!WARNING]
> MCMR is early software. Its policy catalog and command line may change before the first stable release.

MCMR is a fast code policy engine for whole repositories. A Rust kernel understands the source
tree once. Typed Python rules query shared Polars tables and report precise findings. Rules can
also offer fixes that MCMR verifies before keeping them.

MCMR reads Python, Rust, TypeScript, C, C++, and CUDA. Deterministic checks are local and stateless.
Model judgment, network evidence, and writeback are separate opt-ins.

## Installation

Install the command line application from PyPI.

MCMR requires Python 3.14 or newer. Its primary runtime target is free-threaded Python `3.14t+`,
and standard CPython `3.14+` is supported too. Releases include Linux wheels for CPython 3.14 and
`3.14t`. MCMR itself is developed and rehearsed on `3.14t` with the GIL disabled. An installer may
build dependencies from source when their projects do not publish free-threaded wheels yet.

```sh
pip install mcmr
mcmr check .
```

Use `uv tool install mcmr` for an isolated command line installation.

## What it is

- One repository parse feeds every selected rule.
- Each rule runs once over a typed table instead of once per object.
- The default lane contains 241 deterministic rules and makes no model or network request.
- Contextual rules and external evidence run only when explicitly enabled.
- Findings name exact source locations and carry the measurements behind them.
- Safe repairs are reparsed and checked again before MCMR keeps an edit.
- Installed packages can add rules and evidence providers through public entry points.

## Demo

`demo/` is a small Model Context Protocol server written badly on purpose. The baseline reports 50
policy failures across 29 rules. Three prepared stages show how the same repository can converge
while four deliberate findings remain.

Run the baseline without model judgment, network access, repairs, or writeback.

```sh
chefe run check demo/ --no-contextual --format concise --report-only
```

The expected summary is 3 files, 188 facts, 194 executed rules, 50 failures, and 81 findings. See
[demo/README.md](demo/README.md) for the staged walkthrough.

## Usage

Check a repository with deterministic rules.

```sh
mcmr check . --no-contextual
```

Preview fixes without changing files.

```sh
mcmr check . --repair preview
```

Apply only fixes declared safe. MCMR reparses the result and reruns the originating rule before it
keeps an edit.

```sh
mcmr check . --repair apply
```

Enable model judgment or network evidence only when the run needs them.

```sh
mcmr check . --contextual
mcmr check . --external
mcmr check . --contextual --external
```

Inspect the policy catalog and machine-readable output.

```sh
mcmr catalog
mcmr coverage
mcmr replacement
mcmr check . --format json
```

## DataHub

The bundled DataHub provider turns schemas, lineage, ownership, and governance into typed facts.
Rules join that catalog context to exact source references. Read access uses GraphQL directly and
does not require a local Model Context Protocol server.

```toml
[tool.mcmr.execution]
external = true

[tool.mcmr.providers.datahub]
server = "http://localhost:8080"
max_assets = 500
```

Set `DATAHUB_GMS_TOKEN` when the service requires authentication, then run the external lane.

```sh
mcmr check . --external
```

Point `recorded` at captured exchanges to run the same rules without a network connection.

```toml
[tool.mcmr.providers.datahub]
recorded = "recordings"
```

Writeback is explicit. It records each verdict as a DataHub assertion result and records the whole
invocation as a successful policy run. Policy failures remain visible in the run properties and
assertion timelines without making a completed MCMR invocation look like an operational crash.

```sh
mcmr check . --external --writeback
mcmr history .
```

The provider keeps no local catalog cache. [examples/datahub](examples/datahub) contains the
recorded integration story and sample output. [docs/agent-read-back.md](docs/agent-read-back.md)
shows how another agent can read the resulting history through DataHub.

## Plugins

A rule package publishes an `mcmr.rules` entry point. An external evidence package publishes an
`mcmr.providers` entry point.

```toml
[project.entry-points."mcmr.rules"]
acme = "acme_mcmr.rules"

[project.entry-points."mcmr.providers"]
acme = "acme_mcmr.provider:AcmeProvider"
```

Provider settings stay in the checked repository configuration. Secrets stay in the provider's
chosen secret source.

## Development

Chefe owns the environment and every project task.

```sh
chefe install
chefe run setup
chefe run lint
chefe run typecheck
chefe run test
chefe run core-lint
chefe run core-test
chefe run architecture
chefe run debug
chefe run contribute
```

MCMR is licensed under Apache 2.0. [SYSTEM.md](SYSTEM.md) describes the contracts and
[ROADMAP.md](ROADMAP.md) records product work that remains.
