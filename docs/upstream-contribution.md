# Upstream contribution draft

The skill and the documentation page below are ready to submit and are still unopened. Review the
text, adjust anything that reads wrong, and post them yourself. The bug reports in
[Filed issues](#filed-issues) are the exception, since those are already open.

There are two drafted contributions, and they are not equal. The first is a reusable DataHub Skill,
which is the one that carries the knowledge. The second is a documentation page holding the queries
that skill depends on.

## Filed issues

Two defects found while integrating were reproduced against a live DataHub Core 1.6.0 quickstart
running `mcp-server-datahub` 0.6.0 and `acryl-datahub` 1.6.0.17, then reported.

| Issue | What it reports |
| --- | --- |
| [acryldata/mcp-server-datahub#192](https://github.com/acryldata/mcp-server-datahub/issues/192) | The version filter logs `does not meet minimum None` for `get_dataset_assertions`, reporting a Cloud-only tool as failing a version comparison. The gating is correct and only the message names the wrong cause. |
| [acryldata/mcp-server-datahub#193](https://github.com/acryldata/mcp-server-datahub/issues/193) | `search` returns bare URNs for assertion entities, because `SearchEntityInfo` in `search.gql` carries no `Assertion` fragment while `entity_details.gql` already has one. |

A third candidate was withdrawn. We had recorded that `get_entities` reports custom assertions as
not found on Core, on the theory that the restli `/aspects` endpoint does not serve `assertionKey`
for assertions written through `upsertCustomAssertion`. Checking it against the live instance
disproved that. All twenty-one of our custom assertions return `assertionKey` from `/aspects` with
HTTP 200, resolve through `/openapi/v3` and GraphQL, pass the SDK `exists()` call the tool gates on,
and come back from `get_entities` complete with `info`, `platform` and `runEvents`. Nothing was
filed. The original claim is corrected in `docs/agent-read-back.md`.

## Primary, a DataHub Skill

`datahub-code-guardian`, a sixth catalog interaction skill for
[datahub-project/datahub-skills](https://github.com/datahub-project/datahub-skills). The complete
skill lives in [contrib/datahub-skills](contrib/datahub-skills), written in that repository's own
layout and house style, with the pull request title and body in
[contrib/datahub-skills/PR.md](contrib/datahub-skills/PR.md).

The five existing skills cover reading and curating the catalog. None of them covers the moment
somebody is about to change a repository that touches governed data, which is where the two halves
of the answer sit in different systems. The skill teaches one loop. Map the code to the catalog,
read what earlier runs already concluded before proposing anything, check the code against schema,
types, ownership, tags and lineage, repair only what column-level lineage proves, verify the repair
by re-running the check, and record every verdict back as a custom assertion so the next agent
inherits it.

It is a genuine contribution because it is useful without MCMR. Every step is documented as a CLI
workflow and hands off to DataHub's own skills the way those five hand off to each other. MCMR
appears once, in a clearly marked section, as one implementation of the check, repair and record
step rather than as a dependency.

Two things in it came out of exercising the Model Context Protocol server against a running DataHub
Core 1.6.0 rather than out of documentation, and both are flagged for the reviewer in the pull
request body.
`get_dataset_assertions` is Cloud gated and additionally hidden behind `DATA_QUALITY_TOOLS_ENABLED`,
so the assertion read on Core goes through GraphQL. That server's `search` tool has no `Assertion`
fragment, so filtering a search to assertions returns bare URNs with no type or description. Both
shape what the skill tells an agent to do, and both are now open upstream as #192 and #193 with
reproductions.

## Secondary, a documentation page

One page, because that is where the remaining friction was. Every GraphQL shape MCMR needed exists
and works. Finding out which one to ask for, and in what nesting, took longer than writing the code
that consumed it. The skill carries a condensed version of these queries in its
`references/catalog-read-reference.md`, so this page is the fuller treatment for integrators who are
not using an agent skill at all.

## Where to open it

`datahub-project/datahub`, under `docs/api/graphql/`, as a new page titled **Reading a dataset for
an agent**. Open it as a pull request rather than an issue, since the whole value is the
copy-pasteable query.

## Issue text, if a discussion is wanted first

> **Title** GraphQL docs lack one complete dataset read for agent integrations
>
> Building a metadata-aware tool against DataHub Core, the first task is always the same. Read one
> dataset with its schema, ownership, domain, field-level tags and glossary terms, column-level
> lineage, and table-level lineage, then join that to something outside DataHub.
>
> Every piece of that is documented, and none of it is documented together. `searchAcrossEntities`
> is shown returning `urn` and little else. Field-level `globalTags` appear in the tags guide as a
> concept rather than as a selection under `schemaMetadata.fields`. `fineGrainedLineages` is
> described in the column-level lineage guide without a query that reads it back. `degree` on
> `searchAcrossLineage` is the field that separates a direct edge from a reachable node, and an
> integrator who misses it builds a lineage graph where everything is adjacent to everything.
>
> The result is that each new integration rediscovers the same five selections by trial against a
> live instance. A single page holding one worked read would remove that entirely.
>
> I would be glad to contribute the page. A draft is below.

## Page draft

````markdown
# Reading a dataset for an agent

An agent integrating with DataHub usually needs one thing before anything else: everything DataHub
knows about a dataset, in as few round trips as possible. This page is that read.

## The catalog page

One bounded search returns the governance an agent reasons over. `count` and `start` page it, and
`skipHighlighting` keeps the response small when the query is a wildcard.

```graphql
query DatasetPage($query: String!, $count: Int!, $start: Int!) {
  searchAcrossEntities(input: {
    query: $query
    count: $count
    start: $start
    types: [DATASET]
    searchFlags: { skipHighlighting: true }
  }) {
    total
    searchResults {
      entity {
        urn
        ... on Dataset {
          properties { description lastModified { time } }
          deprecation { deprecated }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username }
                ... on CorpGroup { urn name }
              }
            }
          }
          domain { domain { urn properties { name } } }
          schemaMetadata {
            fields {
              fieldPath
              type
              description
              globalTags { tags { tag { urn properties { name } } } }
              glossaryTerms { terms { term { urn properties { name } } } }
            }
          }
        }
      }
    }
  }
}
```

Three things are easy to miss here.

`ownership.owners[].owner` is a union, so a query that selects only `urn` silently loses the human
name a report wants to print. Spreading both `CorpUser` and `CorpGroup` is what gets you a usable
identity.

`globalTags` and `glossaryTerms` sit under each entry of `schemaMetadata.fields`, not on the
dataset. A tag applied through the UI may instead live under
`editableSchemaMetadata.editableSchemaFieldInfo`, so an integration that must see every label reads
both and merges them.

`properties.lastModified.time` is epoch milliseconds. Comparing it against a cutoff is how an agent
answers "which assets changed since my last run" without a second API.

## Column-level lineage

Column-level lineage is what proves a rename. When a column disappears from a schema and exactly
one surviving column derives from it, that is evidence rather than a guess, and it is the
difference between a tool that suggests a fix and a tool that can apply one.

```graphql
query FieldLineage($urn: String!) {
  dataset(urn: $urn) {
    urn
    fineGrainedLineages {
      upstreams { urn path }
      downstreams { urn path }
    }
  }
}
```

`path` is the field path, which is what joins back to `schemaMetadata.fields[].fieldPath`, and it
is the only part of this selection a rename proof needs. The `urn` beside it is the parent dataset
URN rather than the `schemaField` URN written into the aspect, so a consumer telling an
intra-dataset rename from a cross-dataset derivation compares that dataset URN, not a field URN.

A dataset carrying no `upstreamLineage` aspect answers `fineGrainedLineages` with `null` rather
than `[]`, and the same holds for `upstreams` and `downstreams` inside an edge. Every optional
collection on this page behaves that way, so read each one as absent rather than empty.

## Table-level lineage

`searchAcrossLineage` answers reachability, and `degree` is what turns it into a graph.

```graphql
query DatasetLineage($urn: String!, $count: Int!, $start: Int!) {
  searchAcrossLineage(input: {
    urn: $urn
    direction: DOWNSTREAM
    query: "*"
    count: $count
    start: $start
    searchFlags: { skipHighlighting: true }
  }) {
    total
    searchResults {
      degree
      entity { urn }
    }
  }
}
```

Keep `degree` equal to one when you are building edges. Every result is reachable from the URN you
asked about, so treating the whole response as adjacency produces a graph where the source appears
to feed the entire warehouse directly, and any impact measure computed over it is wrong in a way
that looks plausible.

## Writing a result back

An agent that concludes something should say so on the asset. Institutional memory is the right
place, because it is additive and editable.

```graphql
mutation AttachAnalysis($urn: String!, $url: String!, $label: String!) {
  addLink(input: { resourceUrn: $urn, linkUrl: $url, label: $label })
}
```

Prefer this over `updateDescription`. A description is usually a sentence a person wrote, and an
agent that overwrites it destroys the context the next reader needs. A link adds a claim beside the
existing ones and leaves the human record intact.

`addLink` is not idempotent. Sending a link an asset already holds fails with a `BAD_REQUEST`
saying so, which means a job that runs twice a day breaks on its second run unless it reads the
existing memory first.

```graphql
query AttachedAnalyses($urn: String!) {
  dataset(urn: $urn) {
    institutionalMemory { elements { url label } }
  }
}
```

An asset that never received a link answers `institutionalMemory` with `null`, so this is another
selection to read as absent rather than empty.
````

## What to say about the source

The page came out of building [MCMR](https://github.com/phvv-me/mcmr), a code policy engine that
joins DataHub context to source facts, for the Build with DataHub Agent Hackathon. Mentioning that
is honest and gives a reviewer somewhere to check the queries actually run. It is not a reason to
merge, so keep it to one line at the end of the pull request description.

## Before submitting

Every query on this page is the one MCMR sends, and every one of them has now been answered by a
DataHub Core 1.6.0 quickstart. `examples/datahub/recordings` holds those answers verbatim.

## Live verification checklist

Each item below was confirmed against that instance, and each one that came back different from
what this page assumed is now written the way the server answered.

1. **Holds.** `upsertCustomAssertion(urn: String, input: UpsertCustomAssertionInput!)` accepts a
   caller-chosen assertion urn and returns it unchanged, so `urn:li:assertion:mcmr-<rule>-<digest>`
   is stable across runs. Sending the same urn twice with different descriptions left one
   assertion under `dataset.assertions` carrying the second description.
2. **Holds.** `UpsertCustomAssertionInput.platform` is a `PlatformInput` of `{urn, name}` and
   `{name: "mcmr"}` resolves to `urn:li:dataPlatform:mcmr` without the platform existing first.
3. **Holds.** `UpsertCustomAssertionInput.type` round-trips as `info.customAssertion.type` while
   `info.type` becomes `CUSTOM`.
4. **Holds, with one relaxation.** `AssertionResultInput.timestampMillis` is `Long`, not `Long!`,
   so MCMR's `$timestampMillis: Long!` variable is accepted at a nullable location. `type` is
   `AssertionResultType!` whose values are `INIT`, `SUCCESS`, `FAILURE` and `ERROR`, and
   `properties` is `[StringMapEntryInput!]` exactly as declared.
5. **Holds, order not preserved.** `properties` come back as `result.nativeResults` with every key
   and value intact, but not in the order they were sent. A consumer must read them as a map, which
   is what MCMR does to find its own `rule` key.
6. **Holds.** `dataset(urn:).assertions(start:, count:)` returns `runEvents(limit:)` directly under
   each assertion, with `total`, `failed`, `succeeded` and the events themselves. Ordering is not
   guaranteed newest-first, so sorting by `timestampMillis` is required rather than optional.

Three things were different from what this page assumed, and each is now documented above.
`FineGrainedLineage.upstreams[].urn` is the parent dataset URN and not a `schemaField` URN. Every
optional collection is spelled `null` rather than `[]` when the aspect behind it was never written.
`addLink` rejects a link the asset already holds, so a repeating job has to read
`institutionalMemory` first.

One more behaviour is worth a sentence in the pull request. `reportAssertionResult` resolves the
asserted entity through an index that `upsertCustomAssertion` reaches about a second later, so a
result reported in the same breath as the assertion it belongs to is rejected with `does not exist
or is not associated with any entity`. Retrying across that window is the only fix available to a
client, and saying so on the page would save the next integrator the same hour.
