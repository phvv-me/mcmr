---
title: "The demo walkthrough"
description: "Fifty failures collapse to four, in three thematic patches, entirely offline."
---

`demo/` is a working Model Context Protocol server, written badly on purpose, that ships inside
the MCMR repository so a fresh checkout has something real to check. It speaks JSON-RPC over
stdio with nothing but the standard library, answers `initialize`, `ping`, `tools/list`, and
`tools/call`, and exposes five small tools.

## One command

From the repository root, with nothing else set up.

```sh
mcmr check demo/ --no-contextual
```

```text
3 files, 188 facts, 194/211 rules, 17 skipped, 194 table queries, 2313 observations,
50 failures, 81 findings, 0 unassessed, kernel 140 ms, rules 525 ms
```

Fifty failures across twenty-nine rules, in under a second of rule time. The server still runs,
and `python demo/smoke.py` proves it after every stage below. `--no-contextual` keeps the run
deterministic, so the same tree always produces the same verdicts.

## What is wrong with the baseline

Two scripts. `mcp_server.py` holds the transport, the router, the session state, the business
logic, and the metrics, all in one file. `mcp_tools.py` holds five handlers copied from each
other. The interesting findings are the ones a linter does not have.

- `ALL-DUPL0005` finds the refusal string the module writes out four times and never names.
- `ALL-FUNC0009` finds the loop nested three deep.
- `ALL-CLAS0004` finds the twelve-field configuration class.
- `ALL-PARA0003` finds `log(message, is_lifecycle, is_timing)`, where a caller can transpose two
  Booleans and nothing will ever tell them.

## Three stages, one theme each

`demo/stages/` holds the convergence as three patches. Apply them in order from the repository
root and rerun the check after each one.

```sh
git apply demo/stages/0001-duplication-and-constants.patch
git apply demo/stages/0002-function-shapes.patch
git apply demo/stages/0003-structure.patch
```

| Stage | Theme | Files | Facts | Failures | Findings |
|---|---|---|---|---|---|
| baseline | the code as shipped | 3 | 188 | 50 | 81 |
| 0001 | duplication and constants | 3 | 190 | 40 | 60 |
| 0002 | function shapes | 3 | 210 | 20 | 37 |
| 0003 | structure | 13 | 449 | 4 | 4 |

**0001, duplication and constants.** Name the repeated literals, name the magic numbers, delete
the decorative banners and the commented-out entry point, cut two essay comments down to one line
each. Ten failures gone, nothing else moved, which is the point of a thematic batch.

**0002, function shapes.** The sixty-line `serve_forever` becomes a read loop over an `answer`
method and one small method per JSON-RPC route. The boolean flag pairs go. The six-parameter
metrics renderer reads its own counters. Twenty more failures gone, and the repository grew ten
functions doing it.

**0003, structure.** The two scripts become the `mcp` package, one class per module. The
twelve-field configuration splits into an identity, a configuration, and a run counter. The
pass-through transport hierarchy and the factory that built a factory both go. Four failures
remain, on purpose.

## What is still open after stage 0003, and why

- **`ALL-COMM0003`** in `mcp/router.py`. The `TODO` marks `resources/list` and `resources/read` as
  unimplemented. Deleting the marker would hide unbuilt protocol surface rather than build it.
- **`PY-CLI0001`** in `mcp_server.py`. Moving off `argparse` means taking a third-party dependency
  into a server whose whole claim is that it needs nothing but the standard library, a trade worth
  making deliberately, not inside a cleanup batch.
- **`PY-TEST0004`** and **`PY-TEST0005`** on `pyproject.toml`, both pytest strictness settings.
  This directory has no pytest suite, only `smoke.py`, so the settings would configure a tool
  nobody runs yet.

A governance tool that cannot hold an open finding is not telling the truth about your code.

## Record every verdict, then read it back

Add `--writeback` and MCMR records every verdict in DataHub, which is where the rest of the story
happens, one rule holding both a passing and a failing verdict at once as `mcp_tools.py` is
deleted in stage 0003 while `mcp/router.py` keeps reporting. See
[What gets published](/mcmr/docs/datahub/what-gets-published/) for what that timeline looks like
from inside DataHub, and [Reading history back](/mcmr/docs/datahub/reading-history/) for the
command below.

```sh
mcmr check demo/ --no-contextual --writeback
mcmr history demo/
```

## Restoring the baseline

```sh
git checkout demo/
```

Or reverse the patches in the order you applied them, `git apply -R demo/stages/0003-structure.patch`
first.

## Try the whole thing with no service at all

```sh
mcmr demo
```

This copies the recorded DataHub example into a fresh workspace, reports what the catalog says
about a pipeline change, previews the one repair the catalog proves, applies and verifies it,
records every verdict as a DataHub assertion, and reads that history back, entirely offline. See
[examples/datahub](https://github.com/phvv-me/mcmr/tree/main/examples/datahub) for the recordings
that make it possible.
