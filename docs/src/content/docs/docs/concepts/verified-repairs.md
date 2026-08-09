---
title: "Verified repairs"
description: "Why a fix only ships after MCMR reparses the result and reruns the rule that found it."
---

A rule declares repair safety once, on `@rule`, as either `safe` or `review`. `FixQuery` never
repeats that declaration, and compilation rejects a rule that declares safety without returning a
fix, or returns a fix without declaring safety. Of MCMR's 285 rules, 32 currently offer a repair.

## What a fix is made of

`FixQuery` carries a summary and three normalized relations.

- **Rewrites** state typed operations, remove, replace, move, unwrap, rename, inline.
- **Nodes** retain the exact source anchors those operations act on.
- **Imports** state bindings the rendered replacement needs.

Nodes and imports default to typed empty relations, so a simple path deletion supplies only its
rewrite relation and nothing else. The query selects the same `fact_id` values that produced the
finding. It never calls the provider again, and the collector materializes only failed repair rows
before converting them into immutable rewrite models.

## Preview, then apply, never both blindly

```sh
mcmr check . --repair preview
mcmr check . --repair apply
```

`--repair preview` never touches a file. `--repair apply` writes only the fixes a rule declared
`safe`, and the application is transactional. MCMR writes one candidate atomically, reparses it,
reruns the originating rule, and keeps the edit only when that exact rule's precise finding
declines on the new source. A `review` fix stays preview-only regardless of the flag, because a
human judgment call is still the anchor for those.

```text
finding → candidate edit → write → reparse → rerun same rule
                                                    │
                                    finding gone ───┼─── finding remains
                                         │                    │
                                    edit kept            edit discarded
```

The Python renderer validates retained source and UTF-8 byte spans, manages runtime,
`TYPE_CHECKING`, and relative imports, and rejects stale source, overlapping edits, incomplete
references, unsupported language operations, or a plain syntax failure. Cross-file moves must name
an existing destination and exact anchors, or the renderer refuses rather than guesses.

## Directory moves are held to a stricter proof

Renaming a variable is a source edit. Collapsing a package path is a structural claim about every
import that touches it, and MCMR treats the two differently on purpose. A safe pathway collapse
must merge package initializers, prove collision freedom, rewrite every import and module
identity, and validate both Python and Rust module semantics. A file move without those proofs is
not offered as an autofix at all, it stays a finding for a person to act on.

## Bound how much one run can change

```sh
mcmr check . --repair apply --maximum-fixes 50
```

`--maximum-fixes` bounds how many verified edits one run applies, which keeps a first repair run
against an unfamiliar repository from rewriting more than you meant to review in one sitting. See
[The demo walkthrough](/mcmr/docs/start/demo-walkthrough/) for what three batches of repair
looked like against a real, if deliberately messy, small codebase.
