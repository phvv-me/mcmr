# Recorded DataHub example

`sample-demo.txt` is what `mcmr demo` printed on one machine, and `sample-report.json` is the
complete machine-readable report of its first step. Both are committed so the result can be read
without running anything.

One nightly rollup, one governed catalog, and no running service. Run it from the repository root.

```sh
mcmr demo
```

The command copies this directory into a fresh workspace, so nothing here is edited and the demo
runs the same way every time.

## The story

`pipeline.py` reads two assets the catalog governs.

- `ecommerce.analytics.orders` is owned and documented, but the query still names `legacy_total`.
  The catalog no longer declares that column, and its column-level lineage says `total` is the one
  column derived from it. `ALL-DATA0002` reports the exact line, and the proof licenses one safe
  rewrite that MCMR previews, applies, reparses, and reruns before keeping.
- `ecommerce.marts.invoices` has no owner and no description, so `ALL-DATA0013` reports the source
  line that depends on it. Nobody can review this change and nobody can say what the numbers mean.
- `customer_email` on `ecommerce.analytics.orders` is tagged `PII` with no glossary term, which
  `ALL-DATA0012` reports as a label nobody can act on.
- `ecommerce.raw.orders` has no owner at all and four assets sit downstream of it, which is
  what `ALL-DATA0011` reports. An unowned leaf costs one team an afternoon while an unowned root
  stops a reporting stack.
- `amount` is read through `CAST(amount AS STRING)` while the catalog declares it a number, which
  `ALL-DATA0003` reports after normalising both spellings through one engine-neutral parser.
- `since` marks the two assets DataHub modified this month as changed, so `ALL-DATA0007` judges
  the work in front of the reviewer rather than the whole catalog behind it.

## The recordings

`recordings/` holds one JSON file per GraphQL operation. Each file is a list of exchanges pairing
the request variables with the exact response envelope the server returned, so replay is a lookup
rather than a simulation.

```json
[{ "variables": { "urn": "..." }, "response": { "data": {}, "extensions": {} } }]
```

`pyproject.toml` selects them and bounds the catalog read to this warehouse.

```toml
[tool.mcmr.providers.datahub]
recorded = "recordings"
query = "ecommerce.*"
```

**Every file here was captured from a running DataHub Core 1.6.0 quickstart**, seeded with the five
ecommerce datasets the story needs and driven through the same five steps `mcmr demo` runs. The
stored `response` is the envelope that instance returned, byte for byte, so nothing on this page
describes a shape a server has not answered. An exchange states only the variables it is keyed by,
which is why a run timestamp never has to be predicted, and re-capturing against another instance
stays a file swap.

`MCMRUpsertAssertion.json` and `MCMRReportAssertionResult.json` record the two mutations
`mcmr check --writeback` posts, one custom assertion per rule and subject pair and one result per
run against it. Both are keyed by no variables at all, because MCMR reads nothing out of either
acknowledgement and a run reports many of them. `MCMRWritebackLinks.json` records the institutional
memory each judged asset already holds and `MCMRWriteback.json` the link it receives when that read
comes back without one, because DataHub refuses a link an asset already carries. Recording is never
part of a check, so only an explicit `--writeback` or a configured `publish_runs` reaches any of
them.

The four `post-openapi-v3-entity-*.json` files record the other half of that same gate. GraphQL has
no mutation for declaring a dataset with a schema, so the fact tables this run consumed, the flow
for the repository, and one job per executed rule go in through the ingestion surface the catalog
itself is loaded through. Those are keyed by no variables either, because an ingestion request is
an upsert whose acknowledgement MCMR does not read. `MCMRWritebackLinks.json`,
`MCMRAssertionHistory.json` and `MCMRWriteback.json` each end with one exchange naming no variables
at all, captured from a dataset the instance holds with no assertion and no memory written against
it, which is what every freshly published fact table looks like on its first run.

`MCMRAssertionHistory.json` records what `mcmr history` reads back, and it is the one recording
that states more than one point in time. Its timelines are four real runs against that instance,
where `ALL-DATA0002` failed while the pipeline still named the retired column and passed on every
run after the repair landed, while `ALL-DATA0003`, `ALL-DATA0007`, `ALL-DATA0009`, `ALL-DATA0011`
and `ALL-DATA0012` stayed failing throughout. That failing-to-passing transition is the whole point
of recording anything, so the example has to contain one.

`ALL-DATA0008` stays skipped. It measures the share of a breaking change's blast radius that no
test evidence covers, and neither the breaking judgment nor the test evidence has an honest source
here. A working-tree diff says a file moved, not that a schema broke, and nothing in this
repository maps a test to the asset it exercises. Reporting a fabricated hundred percent gap would
be worse than reporting nothing, so the rule stays visible as skipped.

`ALL-DATA0006` stays quiet for the same reason. Upstream health needs DataHub assertion results
about the upstream assets themselves, which the seeded catalog does not carry, so the rule passes
vacuously rather than claiming a health signal nobody wrote.
