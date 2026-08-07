# A very complex MCP server in only two scripts

This directory is a working Model Context Protocol server that MCMR is pointed at on purpose. It
speaks JSON-RPC over stdio with nothing but the standard library, answers `initialize`, `ping`,
`tools/list`, and `tools/call`, and exposes five small tools. It is also deliberately
overengineered, and the point of the demo is watching MCMR take it apart.

## One command

From the repository root, with nothing else set up.

```sh
mcmr check demo/ --no-contextual
```

```
3 files, 188 facts, 194/211 rules, 17 skipped, 194 table queries, 2313 observations,
50 failures, 81 findings, 0 unassessed, kernel 140 ms, rules 525 ms
```

Fifty failures across twenty-nine rules, in under a second of rule time. The server still runs, and
the smoke test proves it.

```sh
python demo/smoke.py
```

```
smoke ok: handshake, 5 tools listed, sum_numbers returned 6.5
```

`--no-contextual` keeps the run deterministic, so the same tree always produces the same verdicts
and the arc below is reproducible. Add `--writeback` and MCMR records every verdict in DataHub,
which is where the rest of this document happens.

```sh
mcmr check demo/ --no-contextual --writeback
mcmr history demo/
```

## The three stages

`stages/` holds the convergence as three patches, one thematic batch each. Apply them in order from
the repository root and rerun the check after each one.

```sh
git apply demo/stages/0001-duplication-and-constants.patch
git apply demo/stages/0002-function-shapes.patch
git apply demo/stages/0003-structure.patch
```

`patch -p1 < demo/stages/0001-duplication-and-constants.patch` works the same way if you would
rather not involve Git. Every stage keeps `python demo/smoke.py` passing, which is the contract the
whole exercise is held to.

| Stage | What it fixes | Files | Facts | Failures | Findings |
|---|---|---|---|---|---|
| baseline | the code as shipped here | 3 | 188 | **50** | 81 |
| 0001 duplication and constants | ALL-DUPL0005, ALL-STRI0002, PY-CONS0001, ALL-COMM0001, ALL-COMM0002, PY-TYPE0003 | 3 | 190 | **40** | 60 |
| 0002 function shapes | ALL-FUNC0001/0005/0007/0008/0009/0010, ALL-PARA0001/0003/0004, ALL-NAMI0001, ALL-BRAN0001 | 3 | 210 | **20** | 37 |
| 0003 structure | ALL-MODU0002/0005, ALL-CLAS0001/0004, ALL-FUNC0001/0008, ALL-BRAN0001, ALL-CONT0001/0003, ALL-REAC0002, PY-CLAS0003 | 13 | 449 | **4** | 4 |

The same arc was originally driven as four commits with a `--writeback` after each, so DataHub holds
four points per timeline rather than one. Re-running it that way is what produces the screens below.

## What is wrong with the baseline

Two scripts. `mcp_server.py` holds the transport, the router, the session state, the business logic
and the metrics. `mcp_tools.py` holds five handlers copied from each other. The interesting findings
are the ones a linter does not have.

- `ALL-DUPL0005` finds the refusal string the module writes out four times and never named.
- `ALL-FUNC0009` finds the loop nested three deep.
- `ALL-CLAS0004` finds the twelve-field configuration class.
- `ALL-PARA0003` finds `log(message, is_lifecycle, is_timing)`, where a caller can transpose two
  booleans and nothing will ever tell them.

## Stage 0001, duplication and constants

One theme per batch. Name the repeated literals, name the magic numbers, delete the decorative
banners, delete the commented-out entry point, cut the two essay comments down to one line each, and
target the Python the project actually runs.

```
3 files, 190 facts, 40 failures, 60 findings
demo merged into 194 rules of the MCMR Rulebook, 156 passing and 25 failing here
```

Ten failures gone. Nothing else moved, which is the point of a thematic batch.

## Stage 0002, function shapes

The sixty-line `serve_forever` becomes a read loop over an `answer` method and one small method per
JSON-RPC route. The boolean flag pairs go. The six-parameter metrics renderer reads its own
counters. The transparent one-line wrappers are inlined.

```
3 files, 210 facts, 20 failures, 37 findings
demo merged into 194 rules of the MCMR Rulebook, 165 passing and 16 failing here
```

Twenty more gone, and the repository grew ten functions doing it.

## Stage 0003, structure

The two scripts become the `mcp` package. One class per module. The twelve-field configuration
splits into an identity, a configuration, and a run counter. The pass-through transport hierarchy
and the factory that made a factory go. The last two if-chains become one dispatch mapping.

```
13 files, 449 facts, 4 failures, 4 findings
demo merged into 196 rules of the MCMR Rulebook, 166 passing and 4 failing here
```

## The DataHub tour

Run with `--writeback` first. The quickstart serves GMS on `:8080` and its front end on `:9002`.

- `http://localhost:9002/domain/urn:li:domain:Codebases` — the repository has arrived as a governed
  thing beside every other codebase MCMR has read.
- `http://localhost:9002/pipelines/urn:li:dataFlow:(mcmr,demo,PROD)` — one flow for the run, holding
  the extraction job that wrote every fact table the rules then read.
- `http://localhost:9002/tasks/urn:li:dataJob:(urn:li:dataFlow:(mcmr,rulebook,PROD),all-dupl0005)` —
  the rule's own page in the shared Rulebook, and the best single screen in the demo. A rule is one
  entity for the whole instance, so this page lists every codebase that runs it with the verdict
  each one last got. Run the stages and `lastResult.demo` flips from `FAILURE` to `SUCCESS` while
  another codebase on the same page stays red. One page answers which repositories fire a rule and
  which ones stopped.
- `http://localhost:9002/dataset/urn:li:dataset:(urn:li:dataPlatform:mcmr,demo/facts/module_fact,PROD)`
  — the Stats tab. Row counts are the shape of the refactor. `module_fact` holds 3 rows until stage
  0003 and 13 after it, `class_fact` goes 3 to 13, and `import_binding_fact` goes 14 to 34. Two
  scripts became eleven modules and the graph says so without anybody writing it down.

## What the next agent reads

```sh
mcmr history demo/
```

Nothing here judges the repository. It reads what earlier runs already concluded, so an agent about
to change this code learns which rule has been failing since when, and which repairs already landed,
instead of discovering all of it again.

```
demo/facts/literal_group_fact
  ALL-DUPL0002  passing since 2026-08-07 12:43
  ALL-DUPL0005  passing since 2026-08-07 12:47  previously `the request envelope
                                                could not be accepted` is
                                                written 4 times in this module

demo/facts/call_fact
  PY-CLI0001    failing since 2026-08-07 12:43  `argparse.ArgumentParser` builds a
                                                second CLI schema instead of
                                                exposing typed callables through
                                                Cyclopts
```

`ALL-DUPL0005` is passing since the second run and still carries what it used to say. `PY-CLI0001`
has been failing since the baseline and nothing has touched it since.

## Files remember too

Every rule keeps a second, finer timeline, one row per file it reported. Those rows close
themselves. Each publish reconciles them, so any file a rule no longer reports gets one `SUCCESS`
event carrying `resolution = no longer reported`, and a rule that did not execute closes nothing,
because silence is not a resolution.

The best beat in the whole demo is one rule holding both states at once.

```
  ALL-COMM0003  failing since 2026-08-07 12:43  `TODO` marks unresolved work in
                                                this comment group
  ALL-COMM0003 mcp/router.py  failing since 2026-08-07 12:56  `TODO` marks
                                                              unresolved work in
                                                              this comment group
  ALL-COMM0003 mcp_tools.py  passing since 2026-08-07 13:07  previously `TODO`
                                                             marks unresolved
                                                             work in this
                                                             comment group |
                                                             `FIXME` marks
                                                             unresolved work in
                                                             this comment group
```

One rule, two files, opposite verdicts, both true. `mcp_tools.py` no longer exists after stage 0003,
so its row closed itself and kept what it used to say. `mcp/router.py` still carries the `TODO`.
Nobody wrote either line by hand.

The run that closes a file says so on its receipt, once.

```
demo closed 64 file verdicts
```

Rerunning the same tree prints nothing, because there is nothing left to close, which is how you
know the reconciliation is idempotent rather than rewriting history on every pass.

## What is still open after stage 0003, and why

Four findings survive on purpose. You do not fix everything in one run, and a governance tool that
cannot hold an open finding is not telling the truth.

- **`ALL-COMM0003`** in `mcp/router.py`. The `TODO` marks `resources/list` and `resources/read` as
  unimplemented. Deleting the marker would hide unbuilt protocol surface rather than build it, so
  the marker stays until the resources lane exists.
- **`PY-CLI0001`** in `mcp_server.py`. Moving off `argparse` means taking a third-party dependency
  into a server whose whole claim is that it needs nothing but the standard library. That is a trade
  worth making deliberately, not inside a cleanup batch.
- **`PY-TEST0004`** and **`PY-TEST0005`** on `pyproject.toml`. Both ask for pytest strictness
  settings. This directory has no pytest suite, only `smoke.py`, so the settings would configure a
  tool nobody runs. They become real the day a suite lands.

## How this directory stays out of MCMR's own check

`demo/pyproject.toml` is the config MCMR reads when the scan root is `demo/`, which is what turns
the contextual lane off and points the DataHub provider at the local quickstart. It also switches
the general purpose linter off here, because this code is a subject rather than a contribution.

The repository's own `mcmr check .` must not judge this code, and the kernel's only project-level
path exclusion is the Git ignore contract, read from the nearest ancestor holding a `.gitignore` and
never from above it. The root `.gitignore` therefore names `demo/`, which skips the subtree for
`check .`, while `check demo/` finds `demo/.gitignore` first and treats this directory as its own
contract root, so every rule still fires. The files are tracked with `git add -f demo`, because Git
honors its index over the ignore file while the kernel only ever reads the file.

## Restoring the baseline

```sh
git checkout demo/
```

Or reverse the patches in the order you applied them.

```sh
git apply -R demo/stages/0003-structure.patch
```
