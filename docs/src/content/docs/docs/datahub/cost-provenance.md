---
title: "Model cost provenance"
description: "Keep token usage attached to the contextual verdict that incurred it."
---

Contextual rules can cost money. MCMR keeps their usage per model turn and per verdict instead of
averaging it across a run.

Each contextual result can record the backend, model, reasoning effort, input tokens, cached input
tokens, and output tokens. Passing and failing verdicts both keep usage because both required model
work.

A batched response may answer many criteria. Its turn is counted once, then linked to the answers
it produced. Cached input remains separate from fresh input so prompt reuse stays visible.

## Rollups

Rule jobs keep totals per codebase, usage for the latest run, and usage across every codebase that
runs the rule. A deterministic rule publishes no cost keys. Missing cost data therefore means the
verdict was computed locally, not that a paid call cost zero.

Measure a candidate model before changing the project default.

```sh
mcmr model-sweep . --backend openrouter --model deepseek/deepseek-v4-flash-0731
mcmr contextual-experiment labels.json
```

`model-sweep` runs the live contextual catalog without editing project configuration.
`contextual-experiment` compares backends against a reviewed label corpus.

See [Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for the backend contract.
