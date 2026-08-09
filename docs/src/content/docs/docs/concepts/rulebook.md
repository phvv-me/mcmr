---
title: "The rulebook"
description: "How 285 rules stay numbered, documented, and searchable, rather than becoming a pile of one-off scripts."
---

A rulebook of hundreds is only useful if a reader can trust the catalog and narrow it fast.
MCMR's catalog tests validate identity, numbering, documentation, policy, dependencies, and
repairs on every rule, built-in or plugin, before it is ever run.

## Every rule carries the same documentation contract

```text
"""{summary}

Definition
----------
{prose}

Evidence
--------
{prose}

Exceptions
----------
{prose}

Examples
--------
{prose}

References
----------
{reference lines}
"""
```

A summary states the judgment in one line. Definition explains what the rule measures. Evidence
says what a finding cites. Exceptions names the documented cases the rule deliberately lets pass.
Examples grounds the abstract definition in something concrete. References is checked against its
own grammar, so a reference is either a URL, a named relation to prior work, `Cites "Practical
Object-Oriented Design"`, or a tool and version such as `ruff B023`, and nothing looser than that
passes catalog construction.

## Explore the catalog without running it

```sh
mcmr catalog
mcmr coverage
mcmr replacement
```

`mcmr catalog` exports the complete typed rule catalog as JSON rather than a maintained, and
inevitably stale, generated registry, one entry per rule with its identity, tables, policy, fixes,
and full documentation. `mcmr coverage` shows what MCMR does about every rule an inventoried
upstream tool ships, native, delegated, adapted, inapplicable, or unavailable, so you can see where
MCMR replaces a linter you already run rather than duplicating it blindly. `mcmr replacement`
audits every frozen legacy rule and capability against its declared successor.

## A rule identifier is also a validated address

```text
mcmr.rules.<scope>.<lane>.<family>.<optional groups>.rNNNN
```

The explicit identifier, `PY-IMPO0003`, stays searchable and stable. The importable path
independently validates the same rule's scope, lane, family, and continuous number, so an
identifier and its code location can never quietly drift apart. See
[Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for what scope and lane mean, and
[Fact tables](/mcmr/docs/concepts/fact-tables/) for the families a rule's path names.

## One rulebook for every codebase that runs it

When writeback is on, every rule is published as one entity for the whole DataHub instance rather
than copied per repository. A rule's own page then lists every codebase that runs it and the
verdict each one last got, which is what makes "which repositories still fail this rule" a page
you open instead of a grep you run. [What gets published](/mcmr/docs/datahub/what-gets-published/)
walks through exactly what that page holds.
