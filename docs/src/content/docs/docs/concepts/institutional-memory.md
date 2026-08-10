---
title: "Institutional memory"
description: "How later agents reuse decisions recorded by earlier checks."
---

An agent should not rediscover which rule failed, whether a repair already landed, or why a change
was refused. MCMR stays stateless by default. With writeback enabled, it records verdicts in
DataHub so the next run can read them first.

```sh
mcmr check . --external --writeback
mcmr history .
```

`mcmr history` reports the latest result per rule and subject, when that state began, prior repairs,
and the last finding. It does not judge the repository again.

## Timelines close explicitly

When a file is repaired, renamed, or deleted, the next publication closes its earlier failing
timeline with a passing event. A rule that did not run closes nothing. Silence is never treated as
proof of resolution.

This lets one rule remain failing for one file while a deleted file records that its old finding
has closed. Repeating the same run creates no extra transition.

## Read only what matters

```sh
mcmr history . --select "ALL-DUPL*"
mcmr history . --assets "urn:li:dataset:(urn:li:dataPlatform:snowflake,orders,PROD)"
```

Direct asset identities skip repository analysis. This is the fastest path when an agent already
knows what it plans to change.

See [Reading history back](/mcmr/docs/datahub/reading-history/) for subject anchoring and
[What gets published](/mcmr/docs/datahub/what-gets-published/) for the stored entities.
