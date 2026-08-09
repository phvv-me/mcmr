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

Our first implementation repeatedly walked Python syntax trees inside rules and could not scale.
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

We plan to broaden verified repair, strengthen contextual evaluation, make DataHub retries more
resilient, support more languages and configuration formats, and guide agents from findings to
proven fixes.
