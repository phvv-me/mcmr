# Devpost submission draft

Plain English, one workflow. Copy the sections below into the Devpost form. Nothing here has been
submitted. The two things this draft cannot produce are the screenshots and the video, and the
capture list at the end says exactly what to shoot.

## Tagline

MCMR reads your code and your DataHub catalog together, repairs what the catalog proves, and
records every verdict back into DataHub so the next agent starts where the last one stopped.

## Category

Agents That Do Real Work, with Metadata-Aware Code Generation and Development as the second fit.

MCMR is the action and writeback engine. DataHub's MCP Server, meaning its Model Context Protocol
server rather than a Metadata Change Proposal, and the Agent Context Kit are how agents consume
what it wrote. A run reads the catalog, decides, repairs what the catalog proves, and records every
verdict back as a custom assertion, and from then on any agent reads that history through DataHub's
own server or the DataHub Skills, with nothing of ours in the reading path.

## Inspiration

We tried to converge one of our own packages, a piece of internal infrastructure nobody had
cleaned up in months. The first scan reported 338 findings. We fixed them with agents, in five
batches, and finished at zero.

What made that possible was not the agents. It was that every batch could see what the previous
batch had concluded. Without that, the second agent reopens the first agent's decisions, argues
with a rule the first one already understood, and reattempts a repair that was already refused for
a good reason. We watched it happen before we fixed it, and it is the single most expensive
failure mode in agent-driven cleanup.

A data pipeline is the same problem with the evidence split across two systems. A renamed column
is the cheapest possible change to make and one of the most expensive to discover. The rename
happens in the warehouse. The breakage happens in a query string inside a Python file, where no
type checker looks and no test fails until the job runs overnight. DataHub knows the column is
gone and knows which column replaced it. The repository knows exactly which line still reads the
old name. Nobody joins the two, and nobody remembers what the last person concluded about either.

## What it does

MCMR is a code policy engine with a Rust kernel that reads a whole repository once, and typed
Python rules that query the result. The DataHub integration gives those rules the organizational
context the repository does not contain, and gives the catalog the enforcement history the
repository cannot keep.

One command runs the whole story with no DataHub service at all.

```
mcmr demo
```

**It finds the risky change.** A nightly rollup reads `legacy_total` from a governed dataset.
DataHub no longer declares that column. MCMR reports the exact file and line, not the asset.

**It explains who is affected.** The same run says the invoices asset this pipeline also reads has
no owner and no description, so there is nobody to review the change and no statement of what the
numbers mean. It says the raw orders table nobody owns has four assets downstream of it. It says a
column tagged PII carries no glossary term, which is a label nobody can act on. Each of those is a
different rule reading a different part of the catalog, and each one points at something a person
can do next.

**It repairs what it can prove.** DataHub's own column-level lineage records that `total` is the
one surviving column derived from `legacy_total`. That is evidence, not similarity. MCMR previews
the one-line rewrite, applies it, reparses the file, reruns the rule that reported it, and keeps
the edit only because the finding is gone. Where the catalog proves nothing, MCMR reports the
problem and offers no patch.

**It records what it concluded, in DataHub's own model.** Every rule and asset pair the run judged
becomes one custom assertion, and the run reports one result against it carrying the measurement,
the findings, and how far the repair got. The assertion identity is derived from the rule and the
asset, so the next run lands on the same assertion instead of creating a second one. This is not a
document only MCMR can read. It is a timeline the catalog already knows how to show and query.

**It reads that history back before anything else touches the file.**

```
mcmr history .
```

```
ecommerce.analytics.orders
  ALL-DATA0002  passing since 2026-08-07 10:00  1 repair applied, previously field
                                                `ecommerce.analytics.orders.legacy_total`
                                                is absent from the catalog schema
  ALL-DATA0012  failing since 2026-08-05 09:00  field
                                                `ecommerce.analytics.orders.customer_email`
                                                tagged `PII` has no glossary term
```

That is the answer to "what has already been tried here". A rule that has been failing since the
fifth is a known problem, not a discovery. A rule that closed with a repair applied is a decision
somebody already made and machine-verified. An agent that reads this does not spend its batch
re-deriving either one.

The whole run takes about one second.

**And any agent reads it back, not only ours.** Because the history is custom assertions rather
than a private file, a Claude Code session with `mcp-server-datahub` pointed at the same instance
asks for the same asset and gets the same verdicts, with no MCMR anywhere in the reading path. Ask
it what is failing on the invoices table and it answers from `nativeResults`, including which rule,
what the measurement was, and whether a repair already landed or was refused.
[docs/agent-read-back.md](agent-read-back.md) is the runnable walkthrough, with the prompts, the
response shapes, and the two rough edges we found in that server while proving it.

## How we built it

A Rust kernel discovers, parses, and normalizes the repository into typed Polars tables. Each rule
runs exactly one query over one table instead of once per object, which is why a repository of
1,800 files and 62,000 facts scans in under four seconds.

DataHub arrives through a typed fact provider. It calls the GraphQL API directly with HTTPX, with
no local agent tool server in the request path and no cached catalog on disk. Reads are a bounded
dataset search for schema, ownership, domain, tags, and glossary terms, column-level lineage for
proven renames, and downstream lineage for impact. Writes are `upsertCustomAssertion` and
`reportAssertionResult` for the timeline, plus one `addLink` per asset as the human receipt.
Nothing calls `updateDescription`, because a description is usually a sentence a person wrote.

Recording is never part of reading. A check returns no evidence of its own unless somebody asks,
which `--writeback` does for one run and a project setting does for a scheduled one. What crosses
that boundary is the run itself, not a rendering of it: one record per rule and asset stating the
verdict, the measurement, the finding count, the repair outcome, and for a contextual rule the
model's reasoning and confidence. Those records come from the report the run already produced, so
recording never analyzes anything twice.

A SQLGlot resolver joins literal SQL inside the source to exact catalog identities. An ambiguous
name stays unresolved rather than becoming a guess, which is the difference between evidence and a
plausible answer.

Rules never see the network. They see typed tables. That boundary is what makes the whole thing
testable without a service, and it is what the recorded catalog in `examples/datahub` replays.

The reading side is deliberately not ours. `chefe.toml` pins `mcp-server-datahub` in its own
environment, and an agent connects that to the same instance to read the assertion timeline back
through DataHub's tools. Doing this for real is how we learned that `get_dataset_assertions` is
gated twice and disappears from `tools/list` on DataHub Core, and that the server's `search` tool
strips assertion results down to bare URNs for `entity_type = assertion`. Both are filed upstream
with reproductions, and the workaround each one implies is what the skill below tells an agent to
do.

## Challenges we ran into

**The tool had to survive its own cleanup.** Converging that infrastructure package meant running
MCMR against a real, messy codebase for days. Roughly twenty rule defects surfaced that way, and
every one of them was a rule that was wrong rather than a codebase that was wrong: a measure that
double-counted, an exception that was documented but not implemented, a repair that produced valid
syntax with the wrong meaning. Dogfooding did not confirm the rules. It corrected them, and that is
the only reason we trust the 338 to 0 number.

**Silent zeros.** The first version had rules that could never fire. The fact family existed, the
rule ran, and the field it read was never populated, so it reported a clean repository forever. A
rule reporting zero looks exactly like a healthy codebase. Finding those cost more than writing
them, and closing them meant adding real evidence rather than relaxing the rule.

**Type spellings.** DataHub calls a column NUMBER. A SQL cast says DECIMAL. Comparing them naively
reports a disagreement on every correct cast. Both sides now go through one engine-neutral
canonicaliser, so NUMBER and DECIMAL agree while STRING and NUMBER do not.

**Knowing when not to build.** One rule measures the share of a breaking change's blast radius that
no test covers. Neither the breaking judgment nor the test evidence has an honest source here, so
that rule is visibly skipped rather than quietly reporting a fabricated number. An honestly skipped
rule beats a shallow one.

## Accomplishments we are proud of

Three hundred and thirty-eight findings to zero on a real package, in five agent-driven batches,
with every step machine-verified rather than eyeballed. The engine reparses and reruns the
originating rule before it keeps any edit, so nothing in that number rests on a model saying it
fixed something.

MCMR runs its own 215 rules over itself and reports one finding, which is a deliberate deferral we
can name. Every defect this project introduced was caught by the tool it is about, including two
adjacent same-typed parameters in a test helper and a fact model that had quietly grown to nine
fields. While building this submission the same self-scan rejected an eleven-statement function, a
class whose members were out of order, and a package that had started depending on its own parent,
and each one was fixed rather than suppressed.

The repair is the part we are most proud of, because it is the part a linter cannot do. It is safe
only because the catalog proves the rename, and it survives only because the engine reruns the rule
against the rewritten file before keeping the edit.

## What we contributed back

Two things go back upstream, and neither of them is MCMR.

**A DataHub Skill, `datahub-code-guardian`.** DataHub ships five catalog skills, and they cover
reading and curating the catalog. None of them covers the moment somebody is about to change a
repository that touches governed data, which is exactly where the two halves of the answer sit in
different systems. The skill teaches that loop to any agent. Map the code to the catalog, read what
earlier runs already concluded before proposing anything, check the code against schema, types,
ownership, tags and lineage, repair only what column-level lineage proves, verify by rerunning the
check, and record the verdict back as a custom assertion. It hands the read steps off to
`/datahub-search`, `/datahub-lineage` and `/datahub-quality` the way DataHub's own skills hand off
to each other, and it names MCMR once, in a marked section, as one implementation rather than a
dependency. It is written in the datahub-skills repository's own layout and house style and is
ready to open as a pull request, with the complete skill and the pull request body in
[docs/contrib/datahub-skills](contrib/datahub-skills).

**Two issues filed against `mcp-server-datahub`**, each reproduced against a live DataHub Core
1.6.0 quickstart with a minimal script before it was reported.

- [acryldata/mcp-server-datahub#192](https://github.com/acryldata/mcp-server-datahub/issues/192),
  the version filter reports a Cloud-only tool as failing a version check against a minimum of
  `None`, so the log names the wrong cause for a missing `get_dataset_assertions`.
- [acryldata/mcp-server-datahub#193](https://github.com/acryldata/mcp-server-datahub/issues/193),
  `search` returns bare URNs for assertion entities because `SearchEntityInfo` has no `Assertion`
  fragment, while `get_entities` projects assertions in full from the other GraphQL file.

A third suspected defect did not survive verification. We had recorded that `get_entities` reports
custom assertions as not found on Core, and a direct check against the live instance resolved all
twenty-one of ours through the restli `/aspects` endpoint, through `/openapi/v3`, and through the
SDK `exists()` call the tool relies on. Nothing was filed, and the claim was corrected in our own
notes instead.

Alongside them goes a documentation page holding the one complete dataset read an agent integration
needs. Every GraphQL shape we needed exists and works. Finding out which one to ask for, and in
what nesting, took longer than writing the code that consumed it, and the missing `degree` filter
on lineage in particular produces a graph that is wrong in a way that looks plausible.

## What we learned

Metadata is only useful when it is joined to something, and a conclusion is only useful when it
outlives the run that reached it. A catalog on its own tells you a column changed. A repository on
its own tells you where a string lives. Together they tell you which line to open, who to ask, and
what can safely happen next. Written back into the catalog, they also tell the next agent what the
last one already decided, which is the difference between convergence and a loop.

## What is next

Recording verdicts that no governed asset explains, by anchoring the run to a DataHub DataJob, so
a structural rule or a contextual judgment leaves a timeline too. Contextual rules that read the
catalog as evidence rather than only the repository, which is the only way to ask whether a
description still describes what a pipeline does. Comparing a run against its own recorded history
inside the engine, so a rule can report that it regressed rather than that it failed. And a
documentation contribution back to DataHub with the GraphQL reads an agent integration needs, which
is drafted and waiting for a live schema check beside the skill and the two issues filed against
`mcp-server-datahub`.

## Try it

```sh
git clone <repository>
cd mcmr
chefe install && chefe run setup
mcmr demo
```

No DataHub instance, no credentials, no network. Point it at a real one by replacing `recorded`
with `server` in the project configuration.

## Pre-submission compliance checklist

Everything the rules require, in the order it is cheapest to check. Nothing here is submitted yet,
and each line is something a person has to confirm in a browser.

- [ ] **Repository is public.** Settings, General, Danger Zone, Change visibility. A judge who hits
      a 404 scores nothing, and the Devpost project URL points straight at it.
- [ ] **Apache 2.0 is visible in the GitHub About sidebar**, not only as a `LICENSE` file. GitHub
      shows the license there once it detects the file, so open the repository home page and read
      the right-hand panel rather than trusting the file exists.
- [ ] **Video is three minutes or shorter.** The current cut targets two forty, which leaves room.
- [ ] **Video is on YouTube or Vimeo and public.** Unlisted is acceptable to most judges but public
      is what the rules ask for, and it must play with no login, no age gate, and no region block.
      Open it in a private window to confirm.
- [ ] **Video is embedded in the Devpost submission**, not only linked in the description.
- [ ] **Project URL is filled in** with the public repository link, and the "Try it" commands in
      this description work from a clean clone.
- [ ] **Built during the hackathon window.** MCMR began on July 23, 2026, which is inside it, and
      the commit history shows that without any claim needing to be made.
- [ ] **Feedback survey opt-in is ticked** on the submission form. It is the bonus prize and it
      costs one checkbox.
- [ ] **Screenshots uploaded**, in the order listed below, with the first one legible at thumbnail
      size.
- [ ] **The datahub-skills pull request is open before submitting**, so a judge can inspect the
      contribution rather than take our word for it. Everything is staged in
      `docs/contrib/datahub-skills`, and `PR.md` there is a fork, a copy, and one `gh pr create`
      away. Opening it stays a person's call.
- [ ] **Upstream contributions are linked** from the submission, which is that pull request plus
      the two issues already filed against `mcp-server-datahub`.
- [ ] **Submitted before the deadline**, since Devpost closes the form on the hour and a finished
      project that missed it scores the same as no project.

## The second demo, a codebase converging

`mcmr demo` shows one repair proved by a catalog. The live arc shows what a governed codebase looks
like over time, and it needs a running DataHub because the whole point is the memory between runs.
`demo/` in this repository is a deliberately overengineered MCP server, two scripts holding transport,
routing, business logic, a twelve-field configuration class, copy-pasted handlers and a refusal
string written out four times. The baseline run reports **50 failures and 81 findings across 29
rules** in 13.8 seconds. Three thematic batches follow, each rerun with `--writeback`, so DataHub
accumulates the timelines rather than replacing them. Naming the duplicated literals and constants
takes it to 40. Giving every function one shape a reader can hold takes it to 20. Splitting the two
scripts into an eleven-module package takes it to **4**, and the smoke test that speaks a real MCP
handshake passes at every stage. What sells it is DataHub, not the terminal. The `ALL-DUPL0005`
page in the shared Rulebook flips `lastResult.demo` to `SUCCESS` while still reporting
`FAILURE` for another codebase, so one page answers which repositories fire a rule and which ones
stopped. The `module_fact` dataset profile plots 3 rows through three runs and 13 on the fourth,
which is what a repository splitting into a package looks like to a governance tool that was never
told it happened. Every rule also keeps a finer timeline, one row per file it reported, and those
rows close themselves. Each publish reconciles them, so a file a rule no longer reports gets one
`SUCCESS` event carrying `resolution = no longer reported`. Sixty-four of this repository's
sixty-eight per-file rows closed that way, which lets one rule hold a failing row for
`mcp/router.py` beside a closed row for the deleted `mcp_tools.py`, both true. Four findings stay
open on purpose, including a `TODO` marking unbuilt protocol
surface and an `argparse` call whose fix means taking a dependency, because a tool that cannot hold
an open finding is not telling the truth. The full script, with every command, timing and UI beat,
is `demo/README.md`, and the three thematic batches ship as patches in `demo/stages/` so the arc
replays with `git apply` rather than git archaeology. A judge who cloned MCMR runs
`mcmr check demo/ --no-contextual` with nothing else set up.

## What the user still has to capture

Screenshots, in this order. Each one should be readable at Devpost thumbnail size, so crop tight.

1. The terminal after `mcmr demo`, scrolled to step 1, showing the seven findings with rule ids and
   the exact file and line. This is the one that has to be legible.
2. The preview diff panel from step 2, showing `legacy_total` becoming `total`.
3. The autofix table from step 3 showing `applied` and `rule verified`.
4. Step 4's recording receipts, showing the per-asset verdict counts and the linked report.
5. Step 5's history, showing `ALL-DATA0002` passing since today with one repair applied beside a
   rule that has been failing since the fifth. This is the second most important shot.
6. A DataHub asset page showing the MCMR custom assertion and its run history, captured against a
   live instance. This is the only screenshot that needs a running DataHub.
7. A Claude Code session with `mcp-server-datahub` connected, answering "what has already been
   tried on this table" from the assertion history MCMR wrote. This is the one that shows the
   knowledge outliving the run, and it needs the same live instance.

Video, two minutes forty at most. Show the product working in the first twenty seconds, which means
opening on `mcmr demo` already running rather than on a title card or an architecture diagram.

- 0:00 to 0:20, the broken pipeline file on screen, then `mcmr demo` and the findings appearing.
- 0:20 to 0:55, read two findings aloud. The missing column and the unowned asset with four things
  downstream. Say who is affected.
- 0:55 to 1:30, the preview diff, then the apply, then the clean rerun. Say that the rename came
  from DataHub's own column lineage and that MCMR reran the rule before keeping the edit.
- 1:30 to 2:10, the recording step, then `mcmr history`, then the DataHub asset page with the
  assertion timeline, then a Claude Code session reading that same timeline through
  `mcp-server-datahub`. Say that this is what the next agent reads first, and that nothing of ours
  is in the reading path.
- 2:10 to 2:40, the 338 to zero story in two sentences, one command to set up, and the skill going
  back to datahub-skills.
