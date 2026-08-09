---
title: "Cost provenance"
description: "What a contextual rule cost, kept per verdict instead of averaged away."
---

A contextual rule is the only kind of rule that costs money to run, and the amount is what tells
an expensive rule apart from a cheap one that fires just as often. The backend already reports its
token usage per candidate, so MCMR keeps that usage per file rather than aggregating it away, and
it travels with the run graph as the spend of the rule job that paid it.

## What one verdict states

Every verdict a contextual rule reaches states `backend`, `model`, `reasoningEffort`,
`inputTokens`, `cachedInputTokens`, and `outputTokens` for the turns behind that verdict alone,
whether the rule failed or passed, because the model was paid either way. A verdict about one file
states what the turns that read that file cost, and the repository-wide verdict states the whole
rule.

A batched assessment answers every criterion in one turn and stamps that one turn on each answer,
so the distinct turns are counted rather than the answers, which is what stops one turn being
billed once per criterion it happened to settle. Cached input travels beside fresh input, because
a harness that reuses a prompt reports almost all of its input as cached, and a rule read as
costing one token flat would be a lie about what actually ran.

## What rolls up, and what stays silent

The rule job rolls the same numbers up per codebase, `tokens.<repo>`, everything that rule has
cost there across its recorded timeline, and `lastRunTokens.<repo>`, what the run that just
finished cost, beside a `totalTokens` rollup across every codebase that runs it. Sorting the
rulebook's properties table by `totalTokens` answers which rule costs the most for what it finds,
directly, without exporting anything.

A deterministic rule states none of these keys at all, rather than a row of zeroes a reader has to
learn to ignore. Silence on cost is itself informative, it says the verdict was computed, not
estimated.

## Comparing backends before you commit to one

```sh
mcmr model-sweep . --backend openrouter --model your-model
mcmr contextual-experiment labels.json --include-sol
```

`mcmr model-sweep` exercises every contextual rule through one configured live backend without
editing the project, which is the cheapest way to see what a candidate backend would have found
and cost before switching the project's default. `mcmr contextual-experiment` goes further,
comparing backends against one complete reviewed label corpus, so a backend swap is a measured
decision rather than a guess. See [Rules and lanes](/mcmr/docs/concepts/rules-and-lanes/) for the
four backends this sweep can exercise.
