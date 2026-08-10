---
title: "What MCMR is"
description: "A repository policy engine built around shared evidence and verified outcomes."
---

MCMR is a policy engine for whole repositories. A Rust kernel reads the source tree once and
stores what it learns in typed tables. Python rules query those shared tables and return precise
findings with source locations.

It reads Python, Rust, TypeScript, C, C++, and CUDA.

## What makes it different

- One repository walk supplies every selected rule.
- Each fact family is extracted once and reused.
- A rule receives only the tables and services named in its signature.
- Providers record primitive evidence and never decide a verdict.
- Contextual models and network providers are opt-in.
- A repair is kept only after parsing and a fresh rule check succeed.

That last property matters when an agent changes code. MCMR does not trust a generated edit just
because it looks plausible. It writes a candidate, reparses it, reruns the rule that found the
problem, and keeps the change only when the finding is gone.

## Extending it

Installed packages can add rules and fact providers through Python entry points.

```toml
[project.entry-points."mcmr.rules"]
acme = "acme_mcmr.rules"

[project.entry-points."mcmr.providers"]
acme = "acme_mcmr.provider:AcmeProvider"
```

Plugin rules use the same typing, documentation, policy, and identity checks as built-in rules.
The DataHub integration uses the same public provider boundary.

Continue with [Install](/mcmr/docs/start/install/), [Fact tables](/mcmr/docs/concepts/fact-tables/),
or the [Rule reference](/mcmr/docs/rules/).
