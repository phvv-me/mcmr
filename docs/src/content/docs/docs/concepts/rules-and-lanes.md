---
title: "Rules and lanes"
description: "Deterministic, contextual, and external, and what each lane is allowed to cost."
---

A rule is one typed function. Required parameters are injected tables or explicit services.
Keyword-only parameters with defaults are user settings a project can override in
`pyproject.toml`. A rule returns one Boolean, count, percentage, category, or contextual query,
and policy belongs to the `@rule` decorator, which a project's own configured policy can override.

```python
@rule("PY-IMPO0003", fix_safety=FixSafety.REVIEW)
def unused_import(subject: Table[ImportBindingFact]) -> OccurrenceQuery:
    ...
```

## Three lanes

| Lane | Answers | Turned on by |
|---|---|---|
| deterministic | Computed from repository structure alone, so it answers the same way twice | On by default |
| contextual | Estimated by a classification backend the caller configured | `--contextual` |
| external | Reads current evidence from a system outside the repository | `--external` |

A rule can need both a classification backend and a network read at once, a DataHub-backed
contextual rule needs `--contextual` and `--external` together. MCMR's own catalog currently holds
285 rules, 241 deterministic and 44 contextual, 20 of which also read external evidence.

```toml
[tool.mcmr.execution]
deterministic = true
contextual = false
external = false
```

## Contextual backends

Four backends answer the same contract, so a batch reaching a new provider changes transport
alone. `gliner2` runs local weights, `codex` and `claude` each run one isolated schema-constrained
process per bounded batch, and `openrouter` posts the same closed schema to an OpenAI-compatible
server, reading its key from `OPENROUTER_API_KEY`.

```toml
[tool.mcmr.contextual]
backend = "codex"
model = "gpt-5.6-terra"
reasoning_effort = "medium"
```

A category a contextual rule can answer states what the model observed, never what MCMR will do
with it. `Category.outcomes(good=..., neutral=...)` names what a project accepts and tolerates,
`Category.advisory()` says every answer is a recommendation, and the `@rule` decorator closes the
partition against the function's own return annotation. Naming a category the annotation does not
hold is refused at declaration, before the rule ever runs.

## Where a rule lives

Every built-in rule sits at a path the catalog validates on its own.

```text
mcmr.rules.<scope>.<lane>.<family>.<optional groups>.rNNNN
```

`<scope>` is `general` or a language such as `python`, `<lane>` is deterministic or contextual,
`<family>` names the fact family the rule is grouped under, and `rNNNN` is a continuous number
inside that family. Duplicate identifiers and numbering gaps fail catalog construction, so the
path is load-bearing rather than a filing convention. See [The rulebook](/mcmr/docs/concepts/rulebook/)
for the documentation contract every rule is held to, and [Verified repairs](/mcmr/docs/concepts/verified-repairs/)
for what a rule declares when it can also fix what it finds.

## A plugin rule looks identical

A rule-only package depends only on `mcmr` and exposes a module through the `mcmr.rules` entry
point group. Discovery imports leaf modules in stable order, and a plugin rule uses the same
identifiers, documentation, typing, numbering, policy, and query validation as a built-in one,
checked against the same path grammar below its own package.

```toml
[project.entry-points."mcmr.rules"]
datahub = "mcmr_datahub.rules"
```

Rule identifiers stay globally unique across every installed package, built-in and plugin alike.
