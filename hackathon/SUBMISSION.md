# My Code, My Rules, the Devpost submission

Copy-paste-ready content for **Build with DataHub, The Agent Hackathon**, metadata track, category
Metadata-Aware Code Generation & Development. Devpost project name is "My Code, My Rules" (MCMR).
This file is submission workspace, not product documentation. The separate recording script lives
in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

## Elevator pitch

Stop Code Slop, put your agent on a leash and know where your code is going.

## Inspiration

We tried to converge one of our own internal tools, a piece of infrastructure nobody had cleaned
up in months. The first scan reported 338 findings. We fixed them with agents, in batches, and
finished at zero using MCMR itself.

What made that possible was not the agents. It was that every batch could see what the previous
batch had already concluded. Without that, the next agent reopens the first agent's decisions,
argues with a rule the first one already understood, and reattempts a repair that was already
refused for a good reason. We watched that happen before we fixed it, and it is the single most
expensive failure mode in agent-driven cleanup.

A data pipeline has the same problem, with the evidence split across two systems. A renamed column
is the cheapest possible change to make and one of the most expensive to discover. The rename
happens in the warehouse. The breakage happens in a query string inside a Python file, where no
type checker looks and no test fails until the job runs overnight. DataHub knows the column is
gone and knows which column replaced it. The repository knows exactly which line still reads the
old name. Nobody joins the two, and nobody remembers what the last person already concluded about
either one. MCMR is the join, and DataHub is where the conclusion gets to outlive the run.

## What it does

MCMR is a code policy engine. A Rust kernel does one pass over a repository and extracts it into
63 typed fact families, exposed to Python as Polars tables. 285 rules then judge those tables
across three lanes, deterministic rules that are pure table computations, contextual rules that
are model-judged through a configured backend such as DeepSeek V4 Flash through OpenRouter, and
external rules that read a connected system. A finding can carry a verified
repair. MCMR previews the change, applies it, reparses the file, reruns the rule that reported it,
and keeps the edit only because the finding is gone.

DataHub is the metadata backbone the rules read and write against, not a bolt-on report.

- Every fact family MCMR extracts becomes a DataHub dataset, schema and all, and 2498 of its
  columns carry real descriptions rather than generic placeholders. Row counts are read as the
  profile they already are, `module_fact` climbs from 3 rows to 13 across the demo's convergence
  arc, and that is a refactor's shape stated by the catalog rather than by us.
- Every rule is one global entity, filed once as a `dataJob` in an instance-wide Rulebook flow, and
  every repository that runs it merges its own verdict onto that same job as `lastResult.<repo>`,
  `findings.<repo>`, `since.<repo>`, and `tokens.<repo>`. One page answers which codebases fire a
  rule and which ones stopped firing it.
- Every verdict becomes a DataHub assertion run event, carrying `nativeResults` with the rule, the
  findings, the repair text, the model's reasoning and confidence where one applies, the lane, and
  the run id that ties it to the invocation that wrote it.
- Per-file timelines close themselves. A file a rule no longer reports gets one passing event
  stating "no longer reported", so a repository never carries a stale red row for code that moved
  on.
- Each writeback run becomes a `DataProcessInstance`, stamped with the same run id, carrying files
  touched, facts read, failures, findings, and per-lane rule counts, plus the wall-clock duration.
- Contextual rules carry full cost provenance, backend, model, reasoning effort, input, cached, and
  output tokens, rolled up per rule per repository, so "which rule costs the most for what it
  finds" is a sortable property rather than a guess.
- A flap detector raises a real DataHub incident when a rule keeps flipping on one file, and the
  run that finally stabilizes the file resolves the incident it opened.
- Fact datasets carry data contracts whose quality clauses are the rule assertions themselves.
- Six typed structured properties, lane, rule family, codebase, findings, tokens spent, and flap
  score, make every one of those metrics filterable across the whole catalog.
- Humans and agents both show up as `corpUser` owners. Pedro Valois is the business owner, the
  running agent is the run actor, and DeepSeek V4 Flash is derived automatically from observed
  spend as the data steward of every contextual rule job.
- A glossary holds 54 rule families under an 11-term core vocabulary, each codebase is filed as a
  child domain under Codebases, and lane and category tags are colored and described rather than
  left as bare strings.

`demo/` is the story in miniature, a deliberately overengineered Model Context Protocol server
built as two Python scripts, not to be confused with DataHub's own use of MCP for a metadata
change proposal. At baseline it fails 50 findings across 29 rules. Three thematic patches later it
holds 4 deliberate survivors, and the entire arc lives in DataHub as history, not just a terminal
log. `mcmr history demo/` reads that institutional memory back before anything else touches the
code, so the next agent learns what earlier runs already concluded instead of rediscovering it one
finding at a time.

And MCMR dogfoods itself. Its deterministic self-check is a required release gate rather than a
claim that lives only in the submission copy.

## How we built it

The kernel is Rust, built on `oxc`, `tree-sitter`, and `ruff_python_parser` for the different
languages MCMR reads, and it hands typed Polars frames to Python through PyO3 and a Maturin
build. A rule runs exactly one query over one table instead of once per object, which is what
keeps a repository scan fast enough to run on every batch instead of once a week.

The DataHub integration ships as an ordinary plugin, `src/mcmr_datahub`, registered through the
same `mcmr.rules` and `mcmr.providers` entry points a third-party package would use. Its provider
calls DataHub's GraphQL API directly over HTTPX, with a SQLGlot resolver that joins literal SQL
inside the source to exact catalog identities, and it leaves an ambiguous name unresolved rather
than guessing. Writes go through `upsertCustomAssertion` and `reportAssertionResult` for the
timeline, `POST /openapi/v3/entity` for schema and lineage, and one `addLink` per asset as the
human-readable receipt. Nothing calls `updateDescription`, because a description is usually a
sentence a person wrote and a tool has no business overwriting it.

Contextual rules build typed candidates from the same tables and hand them to one configured
backend. DeepSeek V4 Flash accepts every rule and candidate through one strict OpenAI style
Responses schema when the complete serialized request fits the configured budget. MCMR
recursively bisects an oversized or unusable request. OpenRouter enables response healing on each
request while MCMR still validates the schema, rule keys, candidate keys, and evidence itself.

Recording is never part of reading. A check produces evidence of its own only when `--writeback`
asks for it, and what crosses that boundary is the run's own report, reused rather than
re-analyzed, so nothing gets judged twice.

We built the whole thing the way we ask it to be used on other code, with lint, type, test, native,
documentation, package-build, and `mcmr check .` gates before a commit lands.

## Challenges we ran into

**The assertion timeline had a race, and it cost thirteen minutes.** DataHub resolves a new
assertion through an index that settles a few seconds after the upsert that created it. Reporting
a result in the same breath as the upsert paid that settling window once per assertion, which
made writeback take thirteen minutes on a repository of any real size. Declaring every assertion
for the run first, then reporting every result second, spends that wait once for the whole batch
instead of once per rule, and the same run now finishes in nine seconds.

**Contextual batching still caused request fan-out.** A batch could hold many candidates, but 44
contextual rules across distinct table graphs still produced many OpenRouter requests. The local
engine finished in under one second while provider turns took minutes. We joined contextual rules
through one virtual repository graph and sent one closed Responses schema when it fit. A packed
DeepSeek V4 Flash rehearsal completed with 10 failures, 13 findings, and 11 unassessed results.

**We were billing the wrong model and did not notice for a while.** The Claude harness has a
safe-mode classifier that runs alongside the real judging model, and our cost provenance was
picking up whichever call happened to answer first, which was usually the classifier, not the
rule's actual verdict. We fixed it by having provenance pick the turn with the greatest output
token count instead of the first one to return, since the classifier's answer is short and the
real judgment is not.

**The kernel found our own tool's blind spot, on ourselves.** While shipping a hackathon feature we
needed a surgical, one-rule regression, and building it surfaced that the kernel's literal grouping
counts an assignment-position literal but misses the same literal sitting inline inside a call
argument. That is exactly the defect class the demo's `ALL-DUPL0005` finding is built to catch, and
we caught it in our own extraction code before it ever reached a rule.

**Hard deletes are not as final as they look.** We hard-deleted 1620 stale catalog entities during
cleanup and later found 6046 orphaned timeseries events still pointing at them. Because assertion
urns are derived deterministically from the rule and the subject, those events would have quietly
resurrected on the next republish rather than staying gone, so a hard delete on DataHub needs its
own timeseries cleanup pass, not just an entity delete.

**DataHub Core 1.6.0 rejects some aspects on a `DataProcessInstance`.** Ownership, glossary terms,
and structured properties all bounce off that entity type on the version we tested against, so the
run record carries everything it can and the richer facets stay on the assertions and datasets
instead, until the platform accepts them.

**The tool caught its own authors, repeatedly.** Three feature waves while building this submission
pushed our own self-check from 1 finding to 41, including a transposable-parameter defect in the
new spend API, two same-typed parameters a caller could swap with nothing to warn them, which is
the exact defect class the demo showcases in its own `log(message, is_lifecycle, is_timing)`
finding. We converged it back down, and every one of those 41 was a real defect, not a false
positive we had to suppress.

## Accomplishments that we're proud of

One of our internal tools converged 338 findings to 0 using MCMR itself, in agent-driven batches,
with every repair reparsed and rerun before it counted. The whole thing runs as a single command,
`mcmr check demo/`, with nothing else to set up.

We are proudest of how much of DataHub's own surface this project uses for real work rather than
as a demo prop, assertions, per-file timelines, DataProcessInstances, incidents, data contracts,
structured properties, glossary terms, domains, colored tags, ownership, and health all carry a
verdict MCMR produced and a reason it produced it.

## What we learned

Metadata is only useful once it is joined to something. A catalog on its own tells you a column
changed. A repository on its own tells you where a string lives. Put together, they tell you which
line to open, who to ask, and what can safely happen next.

And a conclusion is only useful if it outlives the run that reached it. Writing every verdict back
into DataHub as a queryable timeline, rather than a document only MCMR can read, is the difference
between an agent converging a codebase and an agent looping on decisions someone already made.

## What's next for My Code, My Rules

Scan-level path exclusion, version two, so a project can shape what MCMR reads as precisely as it
shapes what a linter reads. Grouping the `CallSite` fact record's nineteen flat fields into the
typed sub-records our own self-check keeps pointing at, the one documented finding we defer on
purpose. Teaching the kernel's literal grouping to count a literal sitting inline in a call
argument, the blind spot we found in ourselves during this hackathon. Richer
`DataProcessInstance` records once DataHub accepts ownership, glossary, and structured-property
aspects on that entity type. And publishing more codebases into the shared Rulebook, so
cross-repository rule analytics keep compounding across our own tools and the demo.

## Built with

- rust
- python
- polars
- pydantic
- datahub
- graphql
- openapi
- pyo3
- maturin
- sqlglot
- httpx
- rich
- cyclopts
- oxc
- tree-sitter
- ruff
- hypothesis
- pytest
- claude
- claude-code
- mcp
- docker
- astro

## Try it out

- Repository, https://github.com/phvv-me/mcmr
- One command demo, `mcmr check demo/`

## Appendix

Working material for us before the form gets submitted, not Devpost copy.

### Pre-submission checklist

The submission window closes August 10, 2026 at 5 PM EDT, which is August 11 at 6 AM JST. Nothing
below is checked yet.

- [x] **Repository is public.** The canonical URL is https://github.com/phvv-me/mcmr.
- [ ] **Apache 2.0 is visible in the GitHub About sidebar**, not only as a `LICENSE` file. Open the
      repository home page and read the right-hand panel rather than trusting the file exists.
- [ ] **Video is three minutes or shorter**, on YouTube or Vimeo, public, and playable with no
      login, no age gate, and no region block. Open it in a private window to confirm.
- [ ] **Video is embedded in the Devpost submission**, not only linked in the description.
- [ ] **Project URL is filled in** with the public repository link, and the try it out commands
      above work from a clean clone.
- [ ] **Built during the hackathon window.** MCMR began on July 23, 2026, which is inside the
      allowed July 6 through August 10 development period, and the commit history shows that
      without any claim needing to be made.
- [ ] **Feedback survey opt-in is ticked** on the submission form.
- [ ] **Screenshots uploaded**, in the order in the shot list below, with the first one legible at
      thumbnail size.
- [ ] **DataHub screens recaptured after the integration fixes.** Completed runs must show success
      and the MCMR platform mark must render from the public icon.
- [x] **The datahub-skills pull request is open**, at
      [datahub-project/datahub-skills#112](https://github.com/datahub-project/datahub-skills/pull/112),
      so a judge can inspect the contribution rather than take our word for it. The staged copy in
      `contrib/datahub-skills` matches what was submitted.
- [ ] **Upstream contributions are linked** from the submission,
      [datahub-skills#112](https://github.com/datahub-project/datahub-skills/pull/112) plus the two
      issues already filed against `mcp-server-datahub`.
- [ ] **Submitted before the deadline.** A finished project that misses the form closing scores the
      same as no project.

### Screenshot and video shot list

Screenshots, in this order, each cropped near 3 to 2 and tight enough to read at thumbnail size.

1. The terminal after `mcmr check demo/`, scrolled to the finding list, with rule ids and exact
   file and line. This is the one that has to be legible.
2. The demo flow's Runs tab, with every completed invocation marked successful and the policy
   failure property falling 50, 40, 41, 40, 20, 4. The bump in the middle is the regression.
3. The intermittent-finding incident on the fact dataset, raised with the observed on and off
   timeline in its description, then its resolution message naming the run that stabilized the
   file.
4. The Rulebook page for `all-dupl0005`, the lane subtype and colored tag, `lastResult.demo`
   flipped to success, `since.demo`, and the "previously said" text still carried.
5. `mcmr history demo/` output, showing a passing rule beside one that has been failing since
   baseline. This is the second most important shot.
6. A contextual rule's job page, the model's reasoning and confidence in the run event beside
   `tokens.demo` and `lastRunTokens.demo`, the cost of the judgment on the same screen as the
   judgment.
7. The `module_fact` dataset's Stats tab, row count climbing 3 to 13 across the arc, the shape of
   the refactor stated by the profile.
8. The same dataset's Schema tab, every column carrying a real description.
9. The dataset's Quality tab, the data contract with rule assertions as its clauses.
10. The Users page, Pedro beside the running agent and DeepSeek V4 Flash, then one entity's ownership
    showing human owner, operating agent, and model steward together.
11. The search page filtered by the `mcmr.lane` structured property, deterministic against
    contextual in one click.
12. The glossary, rule families beside the core vocabulary, one term open showing its attached
    entities.
13. The Codebases domain with the demo child domain and its entity count.
14. The lineage graph from the extract job through the fact tables into the Rulebook, the impact
    analysis view a judge can click through.
15. A Claude Code session reading the assertion history back through `mcp-server-datahub`, with
    nothing of ours in the reading path.

Video, two minutes forty at most. Open on the product already running, not on a title card.

- From second 0 to 20, the deliberately overengineered MCP server on screen, then
  `mcmr check demo/` and fifty findings appearing in under a second.
- From second 20 to 50, read two findings aloud, `log(message, is_lifecycle, is_timing)` where a
  caller can transpose two booleans silently, and the refusal string written four times and never
  named. Say a linter flags neither.
- From second 50 to 1m20s, the three stage patches converge 50 to 40 to 20 to 4 while the DataHub
  Runs tab fills, then the beat in the middle, a regression reintroduces the duplicated string,
  DataHub raises a real incident, and the repairing run resolves it on its own.
- From 1m20s to 1m50s, the Rulebook page for one rule with its verdict timeline and what it
  previously said, then the contextual rule with its reasoning, confidence, and token cost, then
  the Users page where the judging model is the data steward of its own rules.
- From 1m50s to 2m20s, `mcmr history demo/`, then a Claude Code session reading the same timeline
  back through `mcp-server-datahub`. Say this is what the next agent reads first.
- From 2m20s to 2m40s, the 338 to zero story in two sentences, the one command to try it, and the
  skill going back to datahub-skills.
