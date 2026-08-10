---
title: "Incidents and contracts"
description: "Represent unstable findings and repository-wide promises with DataHub entities."
---

Assertion timelines show individual verdicts. Incidents and contracts summarize patterns that
would otherwise require reading many timelines.

## Incidents

A subject is intermittent when collapsed results move from failing to passing and back to failing.
MCMR raises one `Intermittent finding` incident for that rule and subject. Its stable identity
prevents duplicate incidents. A settled timeline resolves it.

Only a subject on a fact dataset published by the same writeback can raise an incident. Each fact
dataset also records a flap score based on its noisiest recent subject.

## Contracts

A contract states what a fact table promises as a whole. Its clauses come from repository-wide
rule verdicts. File-specific verdicts stay out because they describe one location rather than the
table contract.

The contract key is derived from the fact table, so later runs update the same contract. Assertions
are published before clauses that reference them.

An incident answers whether a subject is unstable now. A contract answers what the table should
guarantee when it settles. Both appear on the DataHub asset instead of in a private MCMR report.

Run the write path with the external lane enabled.

```sh
mcmr check . --external --writeback
```

See [What gets published](/mcmr/docs/datahub/what-gets-published/) for the surrounding entity map.
