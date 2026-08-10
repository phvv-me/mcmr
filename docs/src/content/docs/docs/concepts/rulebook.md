---
title: "The rulebook"
description: "How the catalog keeps every rule typed, documented, and searchable."
---

The catalog validates every built-in and plugin rule before execution. It checks identity,
numbering, dependencies, policy, settings, repairs, and documentation.

Every rule docstring follows one contract.

```text
Summary

Definition
Evidence
Exceptions
Examples
References
```

The definition states the judgment. Evidence explains what a finding records. Exceptions describe
intentional quiet cases. Examples make the boundary concrete. References are parsed into named and
linked sources.

The [Rule reference](/mcmr/docs/rules/) is generated directly from these docstrings on every docs
build. Each page links to the exact implementation line and every cited URL. Catalog and docs
therefore cannot drift through manual copying.

## Explore without checking source

```sh
mcmr catalog
mcmr coverage
mcmr replacement
mcmr influence
```

`catalog` exports the typed catalog as JSON. `coverage` maps rules from upstream tools to native,
delegated, adapted, inapplicable, or unavailable support. `replacement` audits frozen legacy
capabilities against successors. `influence` shows which sources shaped the rulebook.

When DataHub writeback is enabled, one shared rule entity records which repositories run it and
their latest verdicts. See [What gets published](/mcmr/docs/datahub/what-gets-published/).
