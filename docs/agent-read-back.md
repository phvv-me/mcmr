# Reading a run back through DataHub's agent tools

MCMR writes what a run concluded into DataHub as custom assertions. This walkthrough is the other
half, where a different agent, in a different session, reads that conclusion back through DataHub's
own Model Context Protocol server before it touches the same pipeline. Nothing here calls MCMR.
That is the point.

The takeaway is one line. **The next agent inherits the knowledge, because the knowledge lives in
DataHub rather than in a session that ended.**

DataHub uses MCP for two different things, Metadata Change Proposal in the ingestion model and the
Model Context Protocol in agent tooling. Every mention on this page is the second one, and the
package it names is `mcp-server-datahub`.

## What you need first

A DataHub Core instance the agent can reach, and at least one MCMR run that recorded against it.

```sh
mcmr check . --external --writeback
```

The server itself is pinned in this repository, so nothing has to be installed globally.

```toml
[envs.datahub-agent]
no-default = true
platforms = ["linux-64"]

[envs.datahub-agent.deps]
python = ">=3.11,<3.12"

[envs.datahub-agent.python.deps]
mcp-server-datahub = ">=0.6,<0.7"
```

```sh
mainboard install datahub-agent --resolve
mainboard run --env datahub-agent -- mcp-server-datahub --help
```

The install provisions the pinned environment and then exits nonzero, because mainboard's Node.js
second stage is workspace wide and looks for `pnpm` inside whichever environment it just
provisioned, and this one declares `no-default` so it carries no Node runtime at all. The
environment it built is complete and the run above works against it, so treat that exit code as
noise until mainboard scopes the second stage to the environments that declare the toolchain.

## Connecting an agent to it

Claude Code reads project scoped servers from `.mcp.json` in the repository root. The command runs
through mainboard so the pinned environment is the one that starts.

```json
{
  "mcpServers": {
    "datahub": {
      "command": "mainboard",
      "args": ["run", "--env", "datahub-agent", "mcp-server-datahub"],
      "env": {
        "DATAHUB_GMS_URL": "http://localhost:8080"
      }
    }
  }
}
```

Set `DATAHUB_GMS_TOKEN` beside the URL when the instance requires authentication. A local Core
quickstart usually does not.

Any other Model Context Protocol client works the same way, since the transport is stdio and the
only configuration is the two environment variables.

## What the server exposes

Against DataHub Core 1.6.0 with `mcp-server-datahub` 0.6.0, `tools/list` returns eight tools.

```
search
get_lineage
get_dataset_queries
get_entities
list_schema_fields
get_lineage_paths_between
search_documents
grep_documents
```

There is a ninth, `get_dataset_assertions`, and it is gated twice. It registers only when
`DATA_QUALITY_TOOLS_ENABLED=true`, and it declares a Cloud minimum version, so the server's version
filter removes it when the connected instance is Core. The server says so in its own log.

```
Filtering out tool 'get_dataset_assertions': server oss version (1, 6, 0, 0) does not meet minimum None
```

That single line decides the shape of the rest of this page. On Cloud the assertion read is one
tool call on that server. On Core it is the same read through the GraphQL endpoint the
`datahub-quality` skill already documents, which is also the read `mcmr history` performs.

## Step 1, ask what the catalog knows

> Use the datahub tools from the Model Context Protocol server. What does DataHub know about the
> dataset `urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.marts.invoices,PROD)`?
> I want its schema, its owners, and its health.

The agent calls `get_entities` with that URN. The response carries the governance an agent reasons
over, and its `health` array is the fast signal that something is failing on the asset.

```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.marts.invoices,PROD)",
  "health": [{ "type": "INCIDENTS", "status": "PASS" }],
  "schemaMetadata": {
    "name": "ecommerce.marts.invoices",
    "fields": [
      {
        "fieldPath": "amount",
        "nativeDataType": "NUMBER",
        "description": "Invoiced amount.",
        "nullable": false
      }
    ]
  }
}
```

This is the read that makes the next question worth asking. The catalog declares `amount` a
`NUMBER`, and the pipeline in `examples/datahub/pipeline.py` reads it through `CAST(amount AS
STRING)`, which is exactly what `ALL-DATA0003` reported and recorded.

## Step 2, read what the last run concluded

> Now read the assertion history on the same dataset. Which checks are attached to it, which are
> failing, since when, and did any of them already apply a repair?

On Cloud, with `DATA_QUALITY_TOOLS_ENABLED=true`, that is one call.

```
get_dataset_assertions(
  urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.marts.invoices,PROD)",
  run_events_count=10
)
```

On Core the same read goes through GraphQL, which is what the `datahub-quality` skill does for
every assertion question.

```sh
datahub graphql --query '
query {
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.marts.invoices,PROD)") {
    assertions(start: 0, count: 50) {
      total
      assertions {
        urn
        info { type description externalUrl }
        runEvents(limit: 10) {
          total failed succeeded
          runEvents {
            timestampMillis status
            result { type nativeResults { key value } }
          }
        }
      }
    }
  }
}' --format json
```

Either route returns the same record, in the shape MCMR writes it. The values below are from the
recorded example run rather than from a live capture, and the identity is derived from the rule and
the asset so a later run lands on it again instead of creating a second one.

```json
{
  "urn": "urn:li:assertion:mcmr-all-data0003-1f3c9a02b4d7",
  "type": "CUSTOM",
  "description": "ALL-DATA0003 field type disagrees with the catalog",
  "externalUrl": "https://github.com/phvv-me/mcmr",
  "platform": "mcmr",
  "latestResultType": "FAILURE",
  "runSummary": { "total": 3, "succeeded": 0, "failed": 3 },
  "runHistory": [
    { "timestampMillis": 1786079034040, "resultType": "FAILURE" }
  ]
}
```

The reason travels in `result.nativeResults`, which the GraphQL read above returns verbatim and the
Cloud tool summarises.

```json
[
  { "key": "rule", "value": "ALL-DATA0003" },
  { "key": "measurement", "value": "1 (allowed <= 0)" },
  { "key": "findings", "value": "1" },
  { "key": "repair", "value": "none" },
  {
    "key": "reasons",
    "value": "field `ecommerce.marts.invoices.amount` expects `TEXT` but the catalog declares `NUMBER`"
  }
]
```

Four fields decide what the reading agent does next, and they are the same four whether the read
came from the server or from GraphQL.

| What                | Where                                         | What it changes                        |
| ------------------- | --------------------------------------------- | -------------------------------------- |
| Current state       | newest `result.type`                          | known problem or new discovery         |
| State since when    | oldest run of the current streak              | regression against long standing debt  |
| Last failure reason | `nativeResults.reasons`                       | which line to open                     |
| Repair outcome      | `nativeResults.repair`                        | `refused` means somebody already said no |

## Step 3, act on it rather than rediscover it

> Given that history, what should I not spend time on, and what is actually new about my change?

A useful answer sounds like the following, and every clause of it comes from the catalog rather
than from the agent's own analysis.

> `ALL-DATA0002` on `ecommerce.analytics.orders` is passing since today and its last run recorded
> `repair=applied`, so the retired column rename is already done and verified. Do not reopen it.
> `ALL-DATA0003` on `ecommerce.marts.invoices` has been failing since the fifth with the same
> reason, so the type disagreement is known debt rather than something your change introduced.
> Nothing here was refused, so no earlier decision blocks you.

That is loop closure. MCMR is the action and writeback engine, and DataHub's Model Context Protocol
server plus the
DataHub Skills are how any agent consumes what it wrote, with no MCMR in the reading path at all.

## Reproducing the tool list

The eight tool names and the filter log line above came from a real `tools/list` against the local
instance, not from documentation.

```python
import asyncio, os
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

os.environ["DATAHUB_GMS_URL"] = "http://localhost:8080"
os.environ["DATA_QUALITY_TOOLS_ENABLED"] = "true"

async def main() -> None:
    async with Client(StdioTransport("mcp-server-datahub", [], env=dict(os.environ))) as client:
        for tool in await client.list_tools():
            print(tool.name)

asyncio.run(main())
```

```sh
mainboard run --env datahub-agent -- python list-tools.py
```

## One rough edge worth knowing

Observed against Core 1.6.0 with `mcp-server-datahub` 0.6.0 and filed upstream as
[acryldata/mcp-server-datahub#193](https://github.com/acryldata/mcp-server-datahub/issues/193).

The server's `search` tool has no `Assertion` fragment in its projection, so a search filtered to
`entity_type = assertion` returns the right count with every result stripped down to its bare
`urn`, while the same filter through `searchAcrossEntities` returns the type and description too.
Estate wide assertion questions therefore go through the CLI on Core, or hydrate each URN through
`get_entities` at the cost of a second round trip.

The other filed defect is cosmetic rather than functional.
[acryldata/mcp-server-datahub#192](https://github.com/acryldata/mcp-server-datahub/issues/192)
covers the `does not meet minimum None` line quoted earlier, where the filter drops
`get_dataset_assertions` for the right reason and then names the wrong one.

An earlier draft of this page claimed a third rough edge, that `get_entities` reports a custom
assertion as not found on Core. That does not hold. Rechecked against the live instance, every
custom assertion MCMR wrote resolves through the restli `/aspects` endpoint, through `/openapi/v3`,
through GraphQL, and through the SDK `exists()` call `get_entities` gates on, and the tool returns
the assertion complete with `info`, `platform` and `runEvents`. Anchoring the read on the dataset
stays the better shape for other reasons, but it is not a workaround for a defect.
