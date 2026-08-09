## Inspiration

Agentic development is fast, but agents are often nearsighted. Local checks rarely show how one
change affects the whole repository. We wanted a leash for LLM agents that keeps human engineering
choices in control. The
[Bun rewrite in Rust](https://bun.com/blog/bun-in-rust) showed how difficult it is to enforce a
style guide across a large agent-written codebase. [Archy](https://github.com/hslee16/Archy) also
inspired our parsing engine. We use MCMR in our own tools to tame agents and considerably reduce
bugs by making them consider both the changed part and the whole software.

## What it does

My Code, My Rules is a repository-wide policy engine. A Rust kernel reads Python, Rust,
TypeScript, C, C++, and CUDA once, then turns the repository into linked, typed fact tables.
Python rules query those tables and report exact locations with supporting measurements.

Deterministic checks are local and enabled by default. Contextual judgment and external evidence
are opt-ins. Contextual checks can use DeepSeek V4 Flash through OpenRouter or local agent
harnesses, with batched repository context. Safe repairs are checked before MCMR keeps them.

With writeback enabled, MCMR publishes schemas, lineage, ownership, run history, costs, incidents,
and verdicts to DataHub. Later runs read that history as evidence of how the codebase evolves.

## How we built it

We translated engineering guidance from books, articles, and established tools into configurable
policies. The Rust kernel uses Oxc, tree-sitter, and Ruff's Python parser. PyO3 and Maturin expose
facts to Python, where Polars executes rules as table queries. DataHub reads use GraphQL and
writeback maps results into assertions, lineage, incidents, tags, and run records.

## Challenges we ran into

Our first design repeatedly walked Python syntax trees inside rules and could not scale.
One shared fact graph moved parsing into Rust and made every rule reuse the same evidence. A DataHub
assertion indexing race also made writeback take minutes. Declaring assertions before reporting
results reduced it to seconds. Verified repair remains limited because an unsafe edit is worse than
a clear finding.

## Accomplishments that we're proud of

MCMR analyzes several languages through one shared model and a small rule authoring interface. The
demo extracts 188 facts from three files and reports 81 findings in under a second. We use it in our
own tools to keep LLM agents aware of architecture, cross-language interfaces, and repository-wide
consequences while letting users configure or reject any policy.

## What we learned

LLMs help with engineering rules that require judgment, but raw source is the wrong context.
Structured metadata lets them reason globally within a bounded prompt. History becomes valuable
when it leads to action. DataHub knows what changed, while MCMR knows where it is used.

## What's next for My Code, My Rules

We plan to broaden verified repair and strengthen contextual evaluation. DataHub retries need to
be more resilient. We also want additional languages and configuration formats, with a direct path
from each finding to a proven fix.

## Submission form answers

### Project URL

[https://phvv.me/mcmr/](https://phvv.me/mcmr/)

This is the public project site. It links to installation, the runnable demo, the DataHub
integration, and the source repository. The direct demo walkthrough is
[https://phvv.me/mcmr/docs/start/demo-walkthrough/](https://phvv.me/mcmr/docs/start/demo-walkthrough/).

### Artifact examples

MCMR generates findings, machine-readable reports, verified source patches, typed fact datasets,
DataHub assertions, and run history. Judges can inspect representative inputs and outputs without
running the project.

- [Deliberately broken MCP server and its three-stage convergence demo](https://github.com/phvv-me/mcmr/tree/main/demo)
- [Recorded DataHub example with GraphQL and OpenAPI exchanges](https://github.com/phvv-me/mcmr/tree/main/examples/datahub)
- [Example pipeline that DataHub metadata can prove how to repair](https://github.com/phvv-me/mcmr/blob/main/examples/datahub/pipeline.py)
- [Agent readback walkthrough with example assertion history](https://github.com/phvv-me/mcmr/blob/main/docs/agent-read-back.md)
- [DataHub Code Guardian skill contribution](https://github.com/datahub-project/datahub-skills/pull/112)

### Which DataHub technologies did you use

Select DataHub Core or OSS, DataHub MCP Server, and DataHub Skills. We also used the DataHub
GraphQL API and OpenAPI ingestion surface directly.

The integration uses datasets and schemas, table and column lineage, ownership, domains, glossary
terms, tags, structured properties, custom assertions and their run events, data contracts,
incidents, institutional memory links, DataFlows, DataJobs, and DataProcessInstances. The product
data plane reads through GraphQL and writes entity aspects through OpenAPI. The MCP server is used
for agent readback. The contributed Code Guardian skill packages the complete read, check, repair,
verify, and writeback loop for other DataHub users.

### DataHub contributions during the hackathon

Yes. We opened one pull request and two reproducible issues.

- [datahub-project/datahub-skills pull request 112](https://github.com/datahub-project/datahub-skills/pull/112) adds the DataHub Code Guardian skill. It is open, mergeable, and its title checks pass.
- [acryldata/mcp-server-datahub issue 192](https://github.com/acryldata/mcp-server-datahub/issues/192) reports a misleading deployment capability message for `get_dataset_assertions`.
- [acryldata/mcp-server-datahub issue 193](https://github.com/acryldata/mcp-server-datahub/issues/193) reports assertion search results that contain bare URNs because the GraphQL search fragment omits the assertion type.

### Pre-existing code and outside work

MCMR began during the hackathon on July 23, 2026. It does not incorporate a pre-existing MCMR
codebase. It builds on open-source libraries and standard developer infrastructure. The native
kernel uses Oxc, tree-sitter, and Ruff's Python parser. PyO3 and Maturin bridge Rust and Python.
Polars, Pydantic, SQLGlot, HTTPX, Rich, and Cyclopts provide the Python data and command surfaces.
DataHub Core 1.6, its GraphQL and OpenAPI interfaces, the DataHub CLI, and
`mcp-server-datahub` provide the metadata system. OpenRouter and DeepSeek V4 Flash provide the
hosted contextual backend used in the final clean-room rehearsal. Claude Code and OpenAI Codex
were used as coding assistants. That rehearsal installs CPython `3.14t` and verifies that the GIL
is disabled before MCMR runs. Archy and Bun's public account of its Rust rewrite influenced the
fact-graph and rule-enforcement ideas, but no code was copied from either project.

### What felt polished or useful in DataHub

The metadata graph was the strongest part of the build. One GraphQL query can return a dataset's
schema, ownership, domain, field tags, glossary terms, and timestamps, while lineage queries add
both table reachability and exact column mappings. Stable custom assertion URNs make repeated
checks accumulate a real timeline instead of creating duplicate reports. DataHub's existing UI
then gives those writes useful homes without a custom dashboard. Rule verdicts appear in assertion
history, invocations appear in the flow Runs tab, fact tables have schemas and profiles, and users
can move through lineage, contracts, incidents, domains, glossary terms, and structured-property
filters. OpenAPI aspect ingestion also made it practical to publish rich entities in batches.

### Where we got stuck or lost time

The GraphQL capabilities worked, but discovering the correct query shapes took longer than writing
the client. Schema fields, editable field labels, ownership unions, fine-grained lineage, and
table-level lineage are documented separately. Optional collections often return `null`, and
`searchAcrossLineage` needs `degree == 1` when reconstructing direct edges. A single complete
dataset-read example would have removed much of that discovery work.

Writeback exposed an eventual-consistency window. Reporting a result immediately after creating a
custom assertion often failed because the assertion was not searchable yet. Paying that delay per
assertion made one early run take thirteen minutes. Declaring the full batch first and then
reporting results reduced the same work to seconds. We also lost time learning that duplicate
`addLink` calls are rejected, hard-deleted entities can leave timeseries events behind, and DataHub
Core 1.6 rejects ownership, glossary, and structured-property aspects on a
`DataProcessInstance`.

### What we would build or fix first with unlimited engineering time

We would make assertion creation and first-result publication atomic and idempotent. Automated
agents need to record hundreds of small verdicts reliably. DataHub should absorb index settling and
the required retries so callers can publish without a read-before-write cycle. A transactional
upsert-and-report API with idempotency keys would make DataHub a much stronger institutional-memory
backend for CI systems and agents. Next, we would publish an aspect capability contract on every
entity type. An integration could then ask whether a `DataProcessInstance` accepts a governance
aspect before attempting the write.

### Bugs, errors, and unexpected behavior

We recorded the following reproducible cases.

- After `upsertCustomAssertion` returned successfully, an immediate `reportAssertionResult` could
  fail with `does not exist or is not associated with any entity`. We expected the successful
  upsert to make the assertion writable. The assertion appeared after the index settled. We now
  declare assertions as a batch and retry bounded result writes.
- On DataHub Core 1.6 with `mcp-server-datahub` 0.6, the server hides the Cloud-only
  `get_dataset_assertions` tool but logs `does not meet minimum None`. We expected a capability or
  deployment message. This is tracked in
  [issue 192](https://github.com/acryldata/mcp-server-datahub/issues/192).
- Searching for assertion entities through the MCP server returns the correct count but only bare
  URNs. We expected the type and description returned for other entities. This is tracked in
  [issue 193](https://github.com/acryldata/mcp-server-datahub/issues/193).
- Repeating `addLink` for an existing institutional-memory link returns `BAD_REQUEST` instead of
  behaving idempotently. We expected a repeated automation run to leave the same link in place.
- Hard-deleting 1,620 stale entities left 6,046 timeseries events referring to their deterministic
  assertion URNs. We expected a hard delete to remove the related history or clearly expose a
  separate cleanup operation.
- DataHub Core 1.6 rejected ownership, glossary-term, and structured-property aspects on
  `DataProcessInstance`. We expected run instances to accept the same governance metadata as the
  datasets and jobs they connect. MCMR keeps those facets on assertions and datasets for now.

## Public links

- Project site and live documentation, [https://phvv.me/mcmr/](https://phvv.me/mcmr/)
- Documentation index, [https://phvv.me/mcmr/docs/](https://phvv.me/mcmr/docs/)
- Installation guide, [https://phvv.me/mcmr/docs/start/install/](https://phvv.me/mcmr/docs/start/install/)
- Demo walkthrough, [https://phvv.me/mcmr/docs/start/demo-walkthrough/](https://phvv.me/mcmr/docs/start/demo-walkthrough/)
- GitHub repository, [https://github.com/phvv-me/mcmr](https://github.com/phvv-me/mcmr)
- Demo source, [https://github.com/phvv-me/mcmr/tree/main/demo](https://github.com/phvv-me/mcmr/tree/main/demo)
- DataHub recorded example, [https://github.com/phvv-me/mcmr/tree/main/examples/datahub](https://github.com/phvv-me/mcmr/tree/main/examples/datahub)
- PyPI package, [https://pypi.org/project/mcmr/](https://pypi.org/project/mcmr/)
- Current version 0.0.2 release, [https://github.com/phvv-me/mcmr/releases/tag/v0.0.2](https://github.com/phvv-me/mcmr/releases/tag/v0.0.2)
- Initial version 0.0.1 release, [https://github.com/phvv-me/mcmr/releases/tag/v0.0.1](https://github.com/phvv-me/mcmr/releases/tag/v0.0.1)
- DataHub Code Guardian contribution, [https://github.com/datahub-project/datahub-skills/pull/112](https://github.com/datahub-project/datahub-skills/pull/112)
- MCP server issue 192, [https://github.com/acryldata/mcp-server-datahub/issues/192](https://github.com/acryldata/mcp-server-datahub/issues/192)
- MCP server issue 193, [https://github.com/acryldata/mcp-server-datahub/issues/193](https://github.com/acryldata/mcp-server-datahub/issues/193)
