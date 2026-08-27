---
title: "Install"
description: "Install MCMR on Python 3.14 or newer and run the first check."
---

MCMR requires Git and Python 3.14 or newer. Standard CPython gives the shortest installation.

```sh
pip install mcmr
mcmr check .
```

Use `uv tool install mcmr` for an isolated command line installation.

## Free-threaded Python

MCMR runs and is tested on free-threaded Python `3.14t+`. Polars does not currently publish a
free-threaded runtime wheel on PyPI. A direct `pip install` therefore tries to compile Polars and
needs a native toolchain.

Use the repository environment to get the compatible conda-forge build without compiling it.

```sh
git clone https://github.com/phvv-me/mcmr.git
cd mcmr
uv tool install mainboard
mainboard install --resolve
mainboard run setup
mainboard run check .
```

The first command runs deterministic rules only. It reads the repository and prints a report. It
does not edit source or contact a model.

## Narrow a first report

```sh
mcmr check . --select "PY-*" --format concise --limit 20
```

`--select` accepts an identifier, prefix, glob, or callable substring. `--format concise` keeps
one finding per line.

## Enable optional work

```sh
mcmr check . --contextual
mcmr check . --external
mcmr check . --contextual --external
```

Contextual rules use the configured model. External rules read a configured provider. A rule may
need both. Run `mcmr backends` before the first contextual check to see which backend and model
will run. [Set up contextual rules](/mcmr/docs/start/contextual-rules/) covers credentials and each
backend.

## Work with repairs

```sh
mcmr check . --repair preview
mcmr check . --repair apply
```

Preview never writes files. Apply keeps only repairs declared safe and verified by a fresh parse
and rule check. See [Verified repairs](/mcmr/docs/concepts/verified-repairs/).

For every option, use [CLI commands](/mcmr/docs/reference/cli/).
