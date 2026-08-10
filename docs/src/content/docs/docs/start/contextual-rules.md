---
title: "Set up contextual rules"
description: "Choose a model backend, provide credentials, and enable model judgment."
---

Contextual rules judge relationships that syntax alone cannot settle. They are off by default and
run only when project configuration or the command line enables them.

## OpenRouter

OpenRouter is the shortest hosted setup. Put the model choice in `pyproject.toml`.

```toml
[tool.mcmr.contextual]
backend = "openrouter"
model = "deepseek/deepseek-v4-flash-0731"
reasoning_effort = "medium"
```

Provide the key to the process, then verify the resolved backend before spending tokens.

```sh
export OPENROUTER_API_KEY="..."
mcmr backends .
mcmr check . --contextual
```

MCMR reads the environment. It does not load a `.env` file itself. Keep secrets outside
`pyproject.toml` and version control.

## Local command backends

The `codex` and `claude` backends call an already installed and authenticated command line tool.
Set `binary` only when its executable has a different name or path.

```toml
[tool.mcmr.contextual]
backend = "codex"
model = "gpt-5.6-terra"
reasoning_effort = "medium"
```

Both command backends run isolated, schema-constrained, single-turn processes. They do not receive
write access from MCMR.

## Local GLiNER2

Use `gliner2` when model weights are already provisioned locally.

```toml
[tool.mcmr.contextual]
backend = "gliner2"
model = "fastino/gliner2-base-v1"
model_path = "/models/gliner2-base-v1"
```

The path must be an existing model directory. GLiNER2 does not use reasoning effort or hosted API
credentials.

## Turn the lane off

`--contextual` and `--no-contextual` override project configuration for one run. External evidence
is separate. A contextual rule that reads DataHub needs both `--contextual` and `--external`.

Continue with [Contextual tuning](/mcmr/docs/reference/contextual-tuning/) before increasing token
budgets.
