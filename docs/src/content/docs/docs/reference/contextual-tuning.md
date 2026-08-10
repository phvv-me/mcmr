---
title: "Contextual tuning"
description: "Control confidence, request packing, token limits, and model runtime."
---

These settings live under `[tool.mcmr.contextual]`. Defaults favor bounded routine checks.

| Setting | Default | Effect |
|---|---:|---|
| `reasoning_effort` | `medium` | Provider reasoning level |
| `timeout_seconds` | `180` | Deadline for one model operation |
| `minimum_confidence` | `0.6` | Answers below this become uncertain |
| `batch_size` | `32` | Candidate slice for process and fallback batches |
| `candidate_budget` | `512` | Maximum answer rows in one OpenRouter pack |
| `prompt_token_budget` | `128000` | Maximum estimated input tokens per pack |
| `max_output_tokens` | `32000` | Provider output cap and planning reserve |

## Pack related rules once

OpenRouter groups rules that depend on shared repository evidence. When all candidates and input
tokens fit, MCMR sends one schema-constrained request instead of repeating the same context for
each rule. Larger repositories split at the candidate or prompt budget.

Keep `prompt_token_budget` below the model context window after reserving output. Increase
`candidate_budget` only when the answer schema and expected failure details still fit the output
cap. Passing judgments omit detailed prose, which keeps grouped responses small.

## Choose output headroom

Reasoning models may count hidden reasoning against output capacity. MCMR reserves part of
`max_output_tokens` according to `reasoning_effort`, then sizes each pack from the remaining answer
budget. A higher effort can therefore produce smaller packs even when the input limit is unchanged.

## Tune safely

Start with the defaults and inspect one run. Raise `timeout_seconds` for slow providers. Raise the
prompt budget only for a model whose context window is known. Lower `minimum_confidence` only when
reviewed labels show that lower-confidence answers are useful.

```toml
[tool.mcmr.contextual]
timeout_seconds = 600
candidate_budget = 768
prompt_token_budget = 640000
max_output_tokens = 384000
```

Token usage, cached input, reasoning effort, and model identity remain attached to findings and
DataHub run records. See [Cost provenance](/mcmr/docs/datahub/cost-provenance/).
