---
title: "Configuration keys"
description: "Every key under [tool.mcmr], read straight from the validated configuration schema."
---

MCMR reads one table, `[tool.mcmr]`, from `pyproject.toml`. A repository with no table at all
gets every default below.

## The top-level table

```toml
[tool.mcmr]
select = ["*"]
ignore = []
```

`select` is a list of identifier or callable patterns, defaulting to everything. `ignore` removes
matches from that selection the same way. Both accept the same pattern grammar `--select` does on
the command line, and a command-line `--select` replaces `select` for that run rather than adding
to it.

## `[tool.mcmr.execution]`

```toml
[tool.mcmr.execution]
deterministic = true
contextual = false
external = false
```

Each key turns one lane on or off. `--contextual` / `--no-contextual` and `--external` /
`--no-external` on the command line override these for one run without editing the file. See
[Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for what each lane means.

## `[tool.mcmr.contextual]`

```toml
[tool.mcmr.contextual]
backend = "codex"
binary = ""
model = "gpt-5.6-terra"
reasoning_effort = "medium"
prompt_token_budget = 128000
# max_output_tokens = 4096
timeout_seconds = 180
minimum_confidence = 0.6
batch_size = 32
```

| Key | Default | States |
|---|---|---|
| `backend` | `codex` | `gliner2`, `codex`, `claude`, or `openrouter` |
| `binary` | unset | Explicit path to the backend binary, when it is not on `PATH` |
| `model` | `gpt-5.6-terra` | The model the backend runs |
| `model_path` | unset | A local directory, for a backend that loads weights directly |
| `reasoning_effort` | `medium` | How hard the model should think |
| `prompt_token_budget` | `128000` | Strict upper bound for one packed request, including its schema |
| `max_output_tokens` | unset | Optional model output allowance reserved beside the packed prompt |
| `timeout_seconds` | 180 | How long one batch may take before it is abandoned |
| `minimum_confidence` | 0.6 | The floor a contextual answer must clear to count |
| `batch_size` | 32 | How many candidates one classification turn batches together |

## `[tool.mcmr.rules.<RULE-ID>]`

```toml
[tool.mcmr.rules.ALL-DUPL0005]
exclude = ["tests"]

[tool.mcmr.rules.ALL-FILE0004]
enabled = true
exclude = ["src/mcmr_datahub/rules", "contrib/datahub-skills"]
```

`enabled` defaults to true, set it false to turn one rule off entirely. `exclude` is a list of
source globs that rule skips, checked against the same identifier the catalog validates. Any other
key under the same table is read as a setting for that rule's own keyword-only parameters, and an
unknown rule identifier or an unknown setting name fails validation rather than being silently
ignored.

## `[tool.mcmr.providers.<name>]`

```toml
[tool.mcmr.providers.datahub]
server = "http://localhost:8080"
sql_dialect = ""
timeout_seconds = 30
recorded = ""
report_url = ""
max_assets = 500
query = "*"
page_size = 50
since = "2026-01-01"
publish_runs = false
owner = "datahub"
domain = "Codebases"
announce = false
frontend = ""
```

The core treats provider settings as validated JSON and never interprets vendor options itself,
each provider defines and validates its own table. The bundled DataHub provider reads `server`
from this table or from the `DATAHUB_GMS_URL` environment variable, and an optional
`DATAHUB_GMS_TOKEN` for a bearer token, never from `pyproject.toml`, so a secret never ends up in a
checked-in file. `recorded` points at a directory of captured GraphQL exchanges instead of a live
server, and requires no environment at all. See [Why metadata](/mcmr/docs/datahub/why-metadata/)
for what `people`, `owner`, `domain`, and `report_url` change about what gets published, and
[Install](/mcmr/docs/start/install/) for turning the provider on for the first time.
