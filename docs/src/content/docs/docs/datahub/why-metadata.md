---
title: "Why metadata"
description: "Why a check writes its conclusion into a catalog instead of keeping its own database."
---

A run that judges a governed asset knows something the next run would otherwise rediscover. MCMR
could keep that knowledge in a private cache, but a cache only MCMR can read is a cache only MCMR
benefits from. DataHub is the catalog most data teams already run, so the conclusion can live
beside the asset it is about, where a data engineer, a governance dashboard, and the next agent
all already look.

```sh
mcmr check . --external --writeback
```

```toml
[tool.mcmr.execution]
external = true

[tool.mcmr.providers.datahub]
server = "http://localhost:8080"
publish_runs = true
```

Publication is never part of reading evidence. A check reads and returns nothing of its own
unless somebody says so, `--writeback` for one run, `publish_runs = true` under the provider for a
scheduled one. The flag is three-valued, so `--no-writeback` suppresses recording a project
already asked for, without editing configuration.

## The fact table is the closest thing a repository has to a subject

A verdict about ordinary source, a duplicated literal, an unused import, needs somewhere to live
that a catalog understands. MCMR publishes the fact dataset a rule queried, `module_fact`,
`call_fact`, and anchors the verdict there. A rule that names a governed identity directly, a
Snowflake table a rule proves is referenced by dead code, keeps storing its verdict on that asset
instead, since that asset is a subject somebody else already owns.

## People, not one shared service account

```toml
[tool.mcmr.providers.datahub.people.human]
id = "you@example.com"
name = "Your name"

[tool.mcmr.providers.datahub.people.agent]
id = "ci-bot"
name = "MCMR CI"
```

A catalog full of work nobody signed is a catalog nobody trusts. The human answers for the
codebase, the agent operates the checks on their behalf, and the two carry different ownership
rather than sharing one account. When a contextual rule ran, the model that judged it is credited
too, `the codex backend`, `gpt-5.6-terra`, as a third attributed identity nobody has to configure,
because it is whatever backend the run actually used. A project that names nobody publishes
nobody, MCMR never invents a person to fill an ownership field.

## Findable on day one

```toml
[tool.mcmr.providers.datahub]
owner = "datahub"
domain = "Codebases"
announce = false
report_url = "https://github.com/your-org/your-repo"
```

An owner and a domain travel with everything a run publishes, both default to something a fresh
DataHub already knows about, which is what puts a first run on the home page instead of only in
search results. `announce = true` also posts one update per repository to the home page feed,
keyed by that repository so a later run rewrites the same post. `report_url` becomes the link an
assertion carries back to wherever your CI report lives, and an unset or placeholder URL writes no
link at all, a link nobody can follow is worse than no link.

## What actually crosses the seam

What crosses is the run itself, not a rendering of it. A `RunRecord` states one rule's verdict
about one subject, the measurement behind it, how many findings it carried, how far its repair
got, and for a contextual rule what the model said and how sure it was. A `RunGraph` crosses
beside it, stating which fact families the run materialized, how many rows each carried, and which
rule declared which columns. Both come straight out of the report the run already produced, so
nothing is analyzed twice, and what a provider stores is exactly what the terminal showed you.
[What gets published](/mcmr/docs/datahub/what-gets-published/) walks through where each of those
lands as a DataHub entity.
