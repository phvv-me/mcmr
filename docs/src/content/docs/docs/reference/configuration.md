---
title: "Configuration"
description: "The validated settings under tool.mcmr in pyproject.toml."
---

MCMR reads `[tool.mcmr]` from `pyproject.toml`. Missing configuration uses safe local defaults.

```toml
[tool.mcmr]
select = ["*"]
ignore = []

[tool.mcmr.scan]
suffixes = []
```

`select` and `ignore` accept identifiers, prefixes, globs, or callable substrings. `suffixes` adds
source extensions to discovery.

## Execution and rule policy

```toml
[tool.mcmr.execution]
deterministic = true
contextual = false
external = false
```

Command flags override these values for one run. [Control rules](/mcmr/docs/reference/rule-control/)
explains selection patterns, lane toggles, exclusions, typed settings, and policy overrides.

## Contextual models

```toml
[tool.mcmr.contextual]
backend = "openrouter"
model = "deepseek/deepseek-v4-flash-0731"
reasoning_effort = "medium"
timeout_seconds = 180
minimum_confidence = 0.6
batch_size = 32
prompt_token_budget = 128000
max_output_tokens = 32000
```

Other fields include `binary` and `model_path`. Supported backends are `gliner2`, `codex`, `claude`,
and `openrouter`. Start with [Set up contextual rules](/mcmr/docs/start/contextual-rules/), then use
[Contextual tuning](/mcmr/docs/reference/contextual-tuning/) for request and token limits.

## Providers

```toml
[tool.mcmr.providers.datahub]
server = "http://localhost:8080"
max_assets = 500
publish_runs = false
```

Each provider validates its own settings. The DataHub provider can also read `DATAHUB_GMS_URL` and
`DATAHUB_GMS_TOKEN`. A `recorded` directory replaces the live server for offline examples.
