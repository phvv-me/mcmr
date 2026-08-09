# Video script

Target length is two minutes and thirty seconds. The terminal stays large enough to read throughout.
The product appears in the first ten seconds and DataHub appears before the first minute.

## Opening from 0 to 20 seconds

Screen shows the repository and immediately runs the deterministic demo check.

> This is My Code, My Rules. Agentic development makes code fast, but tests and ordinary linters
> do not preserve architecture, intent, or decisions across sessions. MCMR gives the repository a
> policy engine the agent can run itself.

```sh
mcmr check demo/ --no-contextual --format concise --report-only
```

Pause on exact file and line findings, then on the summary with 50 policy failures and 81 findings.

## The engine from 20 to 50 seconds

Screen shows the rule catalog, then briefly opens one deterministic rule.

> A Rust kernel reads the repository once and exposes typed fact tables to Python. Two hundred and
> eighty-five rules can check anything from empty directories to dependency direction. The default
> run is deterministic, local, and stateless. Model judgment and network evidence are opt-ins, so
> this command sends no LLM requests.

```sh
mcmr catalog
```

## DataHub memory from 50 to 100 seconds

Screen shows the demo flow, its Runs tab, one rule assertion timeline, and the lineage view.

> A repository does not contain all the evidence an agent needs. DataHub knows schemas, lineage,
> ownership, and governance. MCMR joins those facts to exact source references. With writeback, each
> verdict becomes a DataHub assertion result and each completed invocation becomes a successful
> policy run. Policy violations stay visible as policy data. They do not masquerade as a crashed
> process.

```sh
mcmr check demo/ --external --writeback
mcmr history demo/
```

Pause on the run properties, one assertion history, and the shared run identifier that connects
them.

## A verified change from 100 to 135 seconds

Screen previews one DataHub-backed field rename repair and then shows the verified result.

> MCMR only offers a repair when the evidence proves one outcome. Here, column-level lineage names
> exactly one replacement for a retired field. MCMR previews the edit, applies it, reparses the
> file, reruns the rule, and keeps the change only after the finding closes.

```sh
mcmr check examples/datahub --external --repair preview
```

Use the recorded DataHub example if the live service is unavailable. Do not improvise a network
recovery during the recording.

## Close from 135 to 150 seconds

Screen returns to the banner, repository URL, and the one demo command.

> MCMR gives agents a leash without taking the keyboard away. The code stays yours, the rules stay
> explicit, and DataHub keeps the result available for the next context. My code, my rules.

## Recording checklist

- [ ] Use a clean checkout and increase terminal font size before recording
- [ ] Confirm the baseline summary before recording the final take
- [ ] Confirm DataHub run instances show successful completion
- [ ] Keep every secret and local service token outside the frame
- [ ] Keep the final cut under three minutes
- [ ] Verify the public video in a signed-out browser
