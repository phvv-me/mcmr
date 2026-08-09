---
title: "Incidents and contracts"
description: "What happens when a subject will not stay fixed, and what a table promises as a whole."
---

An assertion timeline is where a verdict lives, and reading one is how a person notices that a
rule keeps changing its mind about a subject. Nobody reads fifty timelines by hand looking for the
one that will not settle, so MCMR raises the two entities DataHub already gives a table's health
and a table's promise.

## Incidents mark a subject that will not settle

A subject alternates when its verdicts, repeats collapsed, go failing, then passing, then failing
again, the smallest pattern no single verdict can explain on its own. Whether the subject is
failing right now comes from what this run itself concluded, since a verdict that just closed a
file has not reached the index a read would go through yet.

```sh
mcmr check . --external --writeback
```

```text
demo raised 2 intermittent findings and resolved 1
```

MCMR raises one incident, typed `Intermittent finding`, titled by the rule and file so a second
run recognizes the one it already opened instead of raising a duplicate, and resolves it the
moment the subject's own history shows it settled. Only a subject on a fact table this same
writeback published is ever considered, raising an incident anywhere else would create a stub
asset nobody asked for. Every published fact table also records a `flapScore`, how many times its
noisiest subject has changed verdict lately, so a reader can sort the tables whose verdicts will
not settle before any single one of them is bad enough to raise on its own.

## Contracts state what a table promises as a whole

A dataset with a hundred assertion timelines under it says what happened. A contract says what is
promised, the question a consumer of the table is actually asking, and DataHub renders it on the
table's own page rather than in a list somebody has to interpret line by line.

The promise is exactly the repository-wide verdict of every rule that read the table whole, a
verdict naming one file stays out of it, since that verdict is about the file rather than the
table. The contract key is derived from the table itself, so a later run updates the same contract
instead of stacking a second one beside it, and its clauses are only ever written after the
assertions they name already exist, because DataHub resolves each one before accepting the
contract.

```text
demo contracted 6 fact tables on 14 rule clauses
```

## Reading both together

An incident tells you a table is noisy right now. A contract tells you what that table is
supposed to guarantee once it settles. Between them, a reader opening a fact table's page for the
first time sees whether anything there is actively unstable and what the table is promising
everyone who queries it, without reading a single rule's history line by line. See
[What gets published](/mcmr/docs/datahub/what-gets-published/) for where `flapScore` sits among
MCMR's other structured properties.
