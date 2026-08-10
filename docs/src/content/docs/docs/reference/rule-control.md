---
title: "Control rules"
description: "Select lanes and rules, exclude paths, and override typed rule settings."
---

MCMR separates temporary command choices from durable project policy.

## Toggle execution lanes

Deterministic rules are on by default. Contextual and external work are off.

```sh
mcmr check . --contextual
mcmr check . --no-deterministic --contextual
mcmr check . --external
```

Persist the same choice in `pyproject.toml`.

```toml
[tool.mcmr.execution]
deterministic = true
contextual = false
external = false
```

An explicit command flag wins for that run. A contextual rule that needs network evidence runs
only when both required lanes are enabled.

## Select or ignore groups

Project selection accepts exact identifiers, prefixes, shell globs, and callable substrings.

```toml
[tool.mcmr]
select = ["ALL-*", "PY-*"]
ignore = ["*-TEST*", "mcmr.rules.python.deterministic.torch"]
```

`mcmr check . --select "PY-TYPE"` temporarily replaces `select`. It does not erase `ignore`.

## Control one rule

```toml
[tool.mcmr.rules.ALL-DUPL0005]
enabled = true
exclude = ["tests/**", "generated/**"]
minimum_occurrences = 5
minimum_length = 12
```

`enabled` removes the rule from execution without changing broader selection. `exclude` supplies
source globs only to that rule. Other keys are typed keyword settings declared by the rule
function. They can also sit under a `settings` table. Repeating a key in both places is invalid.

Unknown rule IDs, setting names, and incompatible values stop before analysis. This makes a knob a
validated policy choice instead of an ignored typo.

## Override result policy

The optional `policy` table changes which typed outputs fail. Its shape must match the rule output,
such as boolean, numeric, category, or set policy. Incompatible policies are rejected.

Use [the complete rule reference](/mcmr/docs/rules/) to find a rule by lane and family. Each page
copies its definition, evidence, exceptions, examples, and references from the implementation
docstring. `mcmr catalog` exports exact settings and effective policy shapes as JSON.
