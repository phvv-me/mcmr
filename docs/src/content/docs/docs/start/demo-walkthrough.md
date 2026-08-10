---
title: "Run the demo"
description: "Check the deliberately messy MCP server included in the repository."
---

The repository includes a small Model Context Protocol server under `demo/`. It is intentionally
messy so a check has real findings. MCMR does not change it unless you request repairs.

Install MCMR and clone the repository with standard Python `3.14+`.

```sh
pip install mcmr
git clone https://github.com/phvv-me/mcmr.git
```

Run every enabled lane and write the results to a local DataHub instance.

```sh
OPENROUTER_API_KEY="..." \
DATAHUB_GMS_URL="http://localhost:8080" \
mcmr check mcmr/demo --contextual --external --writeback --report-only
```

Run the same command again to add another point to each assertion timeline. Then read the history.

```sh
mcmr history mcmr/demo
```

Use `--no-contextual` when you want a fast and repeatable local run. The demo README contains its
smoke command and prepared stages. The [DataHub pages](/mcmr/docs/datahub/why-metadata/) explain
what writeback stores.
