---
title: "Verified repairs"
description: "Why MCMR proves a repair before keeping it."
---

A rule declares repair safety once as `safe` or `review`. A rule cannot return a fix without that
declaration, and it cannot declare repair safety without a fix.

## The repair contract

A fix carries a summary and typed relations for rewrites, source nodes, and required imports.
Operations include remove, replace, move, unwrap, rename, and inline. The selected fact IDs are the
same identities that produced the finding.

```sh
mcmr check . --repair preview
mcmr check . --repair apply
```

Preview never writes a file. Apply considers only `safe` repairs. A `review` repair remains a
proposal unless the caller explicitly allows reviewed changes.

## The proof loop

```text
finding -> candidate -> atomic write -> parse -> rerun the same rule
```

The edit is kept only when parsing succeeds and the precise finding declines. Otherwise the
candidate is discarded.

The renderer also rejects stale source, overlapping edits, invalid spans, unsupported language
operations, and missing imports. Cross-file moves need exact source and destination anchors.

Limit a broad run with `--maximum-fixes`.

```sh
mcmr check . --repair apply --maximum-fixes 50
```

This makes model-assisted cleanup safer because the generated suggestion is never the final
authority. The parser and originating rule are.
