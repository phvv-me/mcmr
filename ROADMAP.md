# Roadmap

MCMR is targeting version 0.0.1 and the
[Build with DataHub Agent Hackathon](https://datahub.devpost.com/). The submission deadline is
August 10, 2026 at 5 PM EDT, which is August 11 at 6 AM JST. The internal feature freeze is August
9 at noon JST so the last day belongs to the demo and submission.

MCMR began on July 23, 2026, inside the allowed July 6 through August 10 development period. The
submission should state that date plainly.

## Product position

The submission is a metadata-aware code guardian.

MCMR reads source structure and DataHub context together. It finds a risky data-code change,
explains the affected assets and owners, repairs what it can prove, reruns the policy, and writes a
useful result back to DataHub for the next person or agent.

The primary category is Agents That Do Real Work. Metadata-Aware Code Generation and Development
is a strong secondary fit because verified fixes produce mergeable code artifacts.

The winning demo is one complete workflow. It is not a catalog of unrelated lint rules and it is
not another chat interface over metadata.

## Foundation already complete

- [x] Rust discovery, parsing, graph, and typed Polars boundary
- [x] One invocation and one lazy query per rule
- [x] Deterministic, contextual, and external execution lanes
- [x] Stateless in-memory execution
- [x] Exact findings with Rich, plain, and JSON output
- [x] Typed rewrite algebra with preview and verified safe application
- [x] Installed rule packages through `mcmr.rules`
- [x] Installed external fact providers through `mcmr.providers`
- [x] Named provider configuration under `tool.mcmr.providers`
- [x] Python, Rust, TypeScript, C, C++, and CUDA frontends
- [x] Upstream inventories, reference accounting, and executable oracle comparisons
- [x] GE4M replacement ledger
- [x] Full lint, typing, Rust, test, and coverage gates before the current work

## Hackathon critical path

### August 3 and 4

- [x] Ship the DataHub integration as a plugin bundle at `src/mcmr_datahub`, with its `ALL-DATA`
      rules under `rules/` and its provider, resolver, and transports under `services/`, registered
      through the public `mcmr.rules` and `mcmr.providers` entry points from the one `mcmr`
      distribution
- [x] Use direct DataHub GraphQL as the runtime integration without a local MCP process
- [x] Keep DataHub credentials outside checked configuration
- [x] Exercise DataHub MCP as the agent integration for discovery and writeback
- [x] Define typed facts for assets, fields, lineage, ownership, and governance
- [x] Load only the fact families selected rules request
- [x] Use the showcase ecommerce datapack for the first end-to-end experiment
- [x] Record DataHub CLI, API, MCP, and documentation friction in the AIZK dev log

### August 5 and 6

- [x] Implement schema existence rules tied to exact SQL source references
- [x] Implement an unowned high-impact asset rule using downstream lineage
- [x] Implement a sensitive-field governance rule using tags and glossary context
- [x] Implement a changed pipeline without matching DataHub documentation or ownership rule
- [x] Give each rule one positive case, one exception, and one end-to-end fixture
- [x] Add one conservative repair that a judge can preview and apply live
- [x] Prove verified writeback with a searchable DataHub Analysis document
- [x] Record every run as a DataHub custom assertion so the enforcement history is queryable in the
      catalog, one assertion per rule and asset pair and one result per run against it
- [x] Read that history back through `mcmr history`, which states per rule whether it is passing or
      failing, since when, how many repairs landed, and why it last failed
- [x] Retire the standalone `writeback` command for `mcmr check --writeback`, which reuses the
      report of the run that just finished instead of analyzing a second time
- [x] Publish the repository's own fact tables, run flow, and one job per executed rule into the
      catalog, so a lineage graph for source code lives where a data team already reads lineage
- [x] Anchor every rule lane's verdict on the fact dataset of its primary table, so a code-only
      repository has a queryable enforcement history rather than only a warehouse-backed one
- [x] Publish every rule once for the whole instance under one `mcmr/rulebook` flow, merging each
      codebase into its inputs and its cross-repository verdict properties, so a rule page answers
      which codebases run it and how much each of them reports
- [x] Make what a run publishes reachable rather than only searchable, through an owner, the
      `Codebases` domain, stated UI subtypes, a platform mark, and an optional home page card
- [ ] Model each run as a `DataProcessInstance` under its rule job, which is the shape DataHub
      already has for run history. The assertion timeline answers the same question today, so this
      is a second version rather than a gap

Four deep rules are enough. More rules only help when they strengthen the same story.

The four are `ALL-DATA0002` missing field, `ALL-DATA0011` unowned high-impact asset,
`ALL-DATA0012` ungoverned sensitive field, and `ALL-DATA0013` ungoverned data reference. Each has a
positive case and an exception case in `tests/data/test_data_asset_rules.py`, and each fires
end to end over the recorded catalog in `examples/datahub`, which the replay tests execute.
`ALL-DATA0003` and `ALL-DATA0007` reach the same recorded run. `ALL-DATA0001`, `ALL-DATA0004`, and
`ALL-DATA0006` keep their unit cases without an end-to-end fixture, and `ALL-DATA0008` is skipped
outright for want of honest change evidence.

The repair is `ALL-DATA0002`. It rewrites the literal naming a retired column so it names the
column DataHub's own column-level lineage proves replaced it, and it is offered only when exactly
one surviving column claims the retired one and the literal spells the old name once. The engine
reparses and reruns the rule before keeping the edit.

### August 7

- [ ] Build one command that starts or connects to the sample DataHub environment
- [x] Build one command that runs the complete MCMR demonstration
- [x] Include the broken input, findings, patch, clean rerun, and DataHub writeback in `examples`
- [x] Ensure the workflow works from a clean checkout with no private service
- [x] Measure cold and warm time and keep the live portion comfortably below one minute

`mcmr demo` copies `examples/datahub` into a fresh workspace and runs all five steps against a
recorded catalog, so nothing starts and nothing is edited in the repository. The five steps now
tell one converging story rather than one pass: what the catalog says, the repair it proves,
that repair applied and verified, every verdict recorded as a DataHub assertion, and the history
the next agent reads before touching the same file. Three consecutive runs took 0.97, 0.96, and
0.97 seconds with no manual recovery, and the command prints its own per-step timings.
`examples/datahub/sample-demo.txt` and `sample-report.json` hold what one run produced.

No command starts a live DataHub yet. The recorded catalog removes the need for one to see the
workflow, and pointing at a real instance is a one-line configuration change, so this stays open
rather than blocking the demo.

### August 8

- [ ] Make one meaningful upstream DataHub contribution
- [x] Prefer a reusable DataHub Skill, connector improvement, SDK fix, or documentation repair found
  while building the integration
- [ ] Open the contribution early enough that judges can inspect it even if review is unfinished
- [ ] Complete the actionable feedback submission

The contribution is drafted in [docs/upstream-contribution.md](docs/upstream-contribution.md) as a
documentation page holding the four GraphQL reads an agent integration needs. It is written and
unsubmitted on purpose, because opening it requires running its queries against a live DataHub
first and because posting to another project is a decision a person makes.

### August 9

- [ ] Freeze features at noon JST
- [x] Run all MCMR and DataHub integration gates from a clean checkout
- [x] Run the demo three times without manual recovery
- [ ] Capture screenshots and sample JSON output
- [x] Write the Devpost description in plain English
- [ ] Record a video no longer than two minutes and forty seconds
- [ ] Show the product working in the first twenty seconds

Sample JSON output is committed. Screenshots are not, and
[docs/devpost.md](docs/devpost.md) lists the six to capture and the shot order for the video.

### August 10

- [ ] Publish the repository under Apache 2.0
- [ ] Make the license visible in the GitHub repository summary
- [ ] Provide exact setup and test commands
- [ ] Provide a free working demo or test path through the judging period
- [ ] Upload the public video and verify it in a signed-out browser
- [ ] Submit early and recheck every link

## Judging plan

The official criteria are equally weighted. Each needs visible evidence.

### Use of DataHub

Read schemas, lineage, ownership, and governance through an approved DataHub agent integration.
Join that context with exact source facts. Write the verified outcome back to the graph. A provider
that only copies metadata into a lint message is too shallow.

### Technical execution

Keep the workflow deterministic where facts suffice. Use contextual judgment only for a genuinely
semantic decision. Show typed provider boundaries, precise locations, one safe repair, a clean
rerun, and complete tests.

### Originality

Position MCMR as the bridge between code policy and the live organizational context graph. DataHub
understands data assets while MCMR understands the repository that creates and consumes them. The
joined graph can answer questions neither system answers alone.

### Real-world usefulness

Use a failure that data platform teams recognize. A renamed or sensitive field reaches a pipeline
change and several downstream assets while ownership is incomplete. The output must tell the
developer what changed, who is affected, and what can safely happen next.

### Submission quality

Keep the README short. Keep setup to one path. Commit sample outputs so judges can understand the
result without running DataHub. The video should follow one story from broken change to durable
resolution.

### Open-source bonus

Contribute one artifact upstream. A small accepted fix or useful Skill is stronger than a large
unreviewed proposal.

## Three-minute demo storyboard

1. Show one pull request with a realistic data pipeline defect.
2. Run MCMR and show exact source evidence plus DataHub lineage and ownership.
3. Preview and apply one proven repair.
4. Rerun MCMR and show the finding closed.
5. Open DataHub and show the result written back for the next agent.
6. End with the one-command setup, tests, and upstream contribution.

## Version 0.0.1 completion

- [ ] Self-scan has no unexplained failures and fewer than one hundred total issues
- [ ] Every selected deterministic rule runs or states an exact provider gap
- [ ] Contextual rules have a reviewed quality sample and explicit cost report
- [ ] `MODU003` previews only cohesive moves into existing sibling modules
- [x] Repair safety is declared once and optional repair relations default cleanly
- [ ] The new suppression rule has a stable preview and semantic cases
- [x] README, system contract, roadmap, changelog, and autofix documentation agree
- [x] `chefe run contribute` passes
- [x] Package builds from a clean checkout
- [x] The DataHub demo passes from a clean checkout

The self-scan reads one finding, and that finding is explained by one commit rather than by new
work. `a62df73` stopped the artifact ignores from swallowing kernel source directories, which put
479 lines of previously ungitted Rust into the scan for the first time and reported fourteen
findings against it. Thirteen of those are now closed.

The graph builder carried twelve of them. It became a `Building` type that absorbs one file at a
time, a `Reachable` type holding the names a reference may land on, and an `exports` package split
into the consumer count, the facade test, and the bypass search, which cleared its statement count,
its cognitive complexity, its nesting depth, and its module width together. The six parameter pairs
a caller could silently transpose became the `References`, `Package`, and `Origin` types and a
`Visibility::narrower` method, so every argument now states the role it plays instead of repeating
the type beside it. `core::calls` and `core::calls::site` no longer import each other, because the
call site names `super::expression::Expression` directly rather than reaching back through the
parent facade for it. The protected region in `src/mcmr/kernel/protocol/exchange.py` narrowed
to one statement by reusing the failure path that class already owned. Nothing in the rule catalog,
the DataHub package, the examples, or the tests reports anything.

The one deferred finding is `ALL-CLAS0004` on `src/core/src/calls/site/mod.rs`, where `CallSite`
declares nineteen fields against a ceiling of seven. Grouping them changes the fact schema, because
the serialized record is what `CallFact.Site` mirrors on the Python side and what twenty-nine call
rules read as columns, and even a `serde` flatten that kept the wire shape identical would still
move a public kernel struct that thirty-four field reads across eleven kernel files depend on. That
is not a change to make in the days before a freeze, so the honest state is one open finding with a
named cause, and the work belongs after submission.

`chefe run contribute` and `chefe run build` both pass, and the demo runs from a clean checkout
with no service. The three remaining unchecked items are contextual and suppression work that the
DataHub submission does not depend on.

## Version 0.0.2 candidates

- Anchor a run that no governed asset explains to a DataHub DataJob, so a rule about repository
  structure or a contextual judgment can be recorded too. Today a verdict needs a governed subject
  to be stored against, which is honest but leaves most of the catalog of rules unrecorded. A
  DataJob standing for the run itself gives those verdicts a home without pretending a Python
  module is a dataset, and the contextual reasoning and confidence a `RunRecord` already carries
  become the properties of that result.
- Contextual rules that read the catalog as evidence rather than only the repository. A model that
  can see an asset's description, its owners, and the code reading it can judge whether the
  description still describes what the pipeline does, which is a question no deterministic rule
  can ask and no catalog field answers on its own.
- Compare a run against its own recorded history inside the engine, so a rule can report that it
  regressed rather than that it failed. The timeline already holds what that comparison needs.
- Track conflicts in the run ledger. Once a run anchors to a DataJob, every verdict lands on a
  timeline keyed by the rule and the subject it judged, and reading that timeline says more than
  any single run does. A subject whose verdict flips back and forth between two runs is being
  pulled by two rules that disagree, and today the only evidence of that is a person noticing the
  same file appear and disappear from a report. Naming the oscillation and the pair of rules
  behind it turns a loop somebody has to spot into a finding the engine reports, which is also
  what makes a repair loop safe to automate rather than something to run once and watch.

## Deferred until after submission

- Typed package relocation for directory pathway collapse
- Incremental source caching
- GPU execution for Polars
- Kernel-side prose language facts using a Rust-native detector
- A web dashboard
- Broad marketplace discovery
- Additional contextual models
- More language frontends

Directory pathway collapse is deferred because moving files without merging initializers and
rewriting every module reference can create a new error while closing the directory finding. It
becomes an autofix only after one typed relocation transaction proves the entire change.

Prose language detection is deferred until the kernel can emit the detected ISO language, script,
confidence, and reliability for each comment and docstring. A Rust-native detector such as
Whatlang avoids a Python 3.14 free-threaded wheel dependency. Contextual judgment should remain a
fallback for ambiguous or mixed-language text instead of making every writing rule pay model cost.
