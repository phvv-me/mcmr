---
title: "Why DataHub"
description: "Keep code policy outcomes beside the assets and lineage they govern."
---

A check learns something the next run would otherwise rediscover. A private cache helps only MCMR.
DataHub lets engineers, dashboards, and later agents read the same conclusion beside the asset it
describes.

```toml
[tool.mcmr.execution]
external = true

[tool.mcmr.providers.datahub]
server = "http://localhost:8080"
publish_runs = true
```

Set `DATAHUB_GMS_TOKEN` when the server requires authentication. Secrets never belong in project
configuration.

## Reading and writing stay separate

External rules can read DataHub without publishing anything. Writeback happens only through
`--writeback` or `publish_runs = true`. `--no-writeback` suppresses a configured default for one
run.

```sh
mcmr check . --external --writeback
```

Ordinary source findings attach to the fact dataset queried by the rule. A rule that names a
governed asset directly stores its verdict on that asset instead.

## Ownership and attribution

Projects can name a human owner and an agent operator. Contextual verdicts also record the actual
backend and model. MCMR invents no identity when none is configured.

An owner, domain, and report URL can make results discoverable from the first run. An unset report
URL stays absent instead of producing a dead link.

What crosses the integration boundary is structured run data. It includes verdicts, measurements,
repairs, facts, lineage, and model usage. The provider does not reanalyze the source.

See [What gets published](/mcmr/docs/datahub/what-gets-published/) for the entity map.
