---
title: "Rules and lanes"
description: "How typed rules separate local checks, model judgment, and network evidence."
---

A rule is one typed function. Required parameters are tables or explicit services. Keyword-only
parameters with defaults are project settings. The return annotation closes the possible result.
Policy belongs to the `@rule` declaration and can be overridden by project configuration.

## Three lanes

| Lane | Work | Enable with |
|---|---|---|
| deterministic | Computes from repository facts | Enabled by default |
| contextual | Asks a configured model for a bounded judgment | `--contextual` |
| external | Reads a configured system outside the repository | `--external` |

A contextual rule may also require external facts. Such a rule needs both flags.

## Contextual backends

`gliner2`, `codex`, `claude`, and `openrouter` implement the same classification contract. A model
answer records its backend, model, confidence, and token usage. MCMR then applies the rule policy.

```toml
[tool.mcmr.contextual]
backend = "openrouter"
model = "deepseek/deepseek-v4-flash-0731"
reasoning_effort = "medium"
max_output_tokens = 32000
```

## Stable identities

Every built-in rule lives at a validated path.

```text
mcmr.rules.<scope>.<lane>.<family>.<groups>.rNNNN
```

The path and explicit identifier must agree on scope, lane, family, and sequence. Duplicate IDs
or numbering gaps stop catalog construction.

Plugin rules follow the same contract. See the [Rule reference](/mcmr/docs/rules/) for every rule
and its source-derived documentation. Use [Control rules](/mcmr/docs/reference/rule-control/) for
selection and per-rule settings.
