# Pull request draft: datahub-code-guardian

Ready to open, not opened. Target repository `datahub-project/datahub-skills`, branch off `main`.

The title matters, since the repository squash merges and enforces Conventional Commits through the `Lint PR Title` check. A new skill is a feature.

```
feat: add datahub-code-guardian skill
```

## Body

> ## What
>
> A sixth catalog interaction skill, `datahub-code-guardian`, for the case where the thing being
> changed is a repository rather than the catalog. It teaches an agent to check code against the
> catalog before an edit lands, apply only repairs the catalog proves, and record the verdict back
> as a custom assertion so the next agent inherits it.
>
> ## Why
>
> The five existing catalog skills cover reading and curating metadata. None of them covers the
> moment a person or an agent is about to change a pipeline, a transformation, or a query living in
> application source. That moment is where a catalog earns its keep, because the two halves of the
> answer sit in different systems. A renamed column is the cheapest change to make and one of the
> most expensive to discover. The rename happens in the warehouse. The breakage happens in a query
> string inside a source file, where no type checker looks and no test fails until the job runs
> overnight.
>
> The second gap is memory. An agent's context ends with its session, so the next one reopens
> decisions the last one already made, re-derives failures that are already known, and reattempts
> repairs that were refused for a good reason. DataHub already has the durable place to put that
> knowledge: `upsertCustomAssertion` and `reportAssertionResult` work on Core, and an assertion with
> a stable caller-chosen URN accumulates a timeline the catalog knows how to show and query. The
> skill makes reading that history the second of five moves, before anything is proposed, and
> writing it back the closing one.
>
> ## The loop
>
> 1. **Map** the code to the catalog. Which governed assets does this repository actually name?
> 2. **Read** the check history on those assets, before proposing anything.
> 3. **Check** the code against catalog facts, which is schema, types, ownership, tags, and lineage.
> 4. **Repair** only what the catalog proves, and verify by re-running the check.
> 5. **Record** every verdict back, passes included.
>
> The judgment the skill turns on sits inside move 4, the line between proven and plausible.
> Column-level lineage recording exactly one surviving derived field for a retired column licenses
> a rewrite. A similar column name does not, and the skill reports those without offering a patch.
>
> ## Hand-offs
>
> The skill delegates rather than duplicating. `/datahub-search` resolves names to URNs,
> `/datahub-lineage` sizes a blast radius, `/datahub-enrich` handles the cases where the honest fix
> is metadata rather than code, `/datahub-quality` takes over when the user wants DataHub to run the
> check itself on a schedule, and `/datahub-setup` owns connectivity. The `Not This Skill` table
> draws the boundary in both directions, including the pair that is easiest to confuse: "what breaks
> if I change orders" is a Lineage question, and "what breaks in this repository if orders changes"
> is this one.
>
> ## Files
>
> ```
> skills/datahub-code-guardian/
> ├── SKILL.md
> ├── README.md
> ├── references/
> │   ├── catalog-read-reference.md
> │   ├── assertion-history-reference.md
> │   └── verdict-writeback-reference.md
> └── templates/
>     └── guardian-report.template.md
> commands/code-guardian.md
> ```
>
> Plus a routing row in `skills/using-datahub/SKILL.md`, a section in `README.md` beside the other
> catalog skills, and a row in the commands table.
>
> ## Notes for the reviewer
>
> Everything in the references was exercised against a running DataHub Core 1.6.0 rather than
> written from memory. Two findings shape what the skill tells an agent to do, and both are now
> filed against `mcp-server-datahub` with reproductions.
>
> - `get_dataset_assertions` is gated twice in `mcp-server-datahub` 0.6.0. It registers only under
>   `DATA_QUALITY_TOOLS_ENABLED=true`, and its declared minimum version is Cloud only, so the
>   version filter drops it from `tools/list` against a Core server. The skill therefore routes the
>   history read through `datahub graphql` on Core and mentions the Cloud tool separately. The filter
>   also names the wrong cause when it does this, which is
>   [acryldata/mcp-server-datahub#192](https://github.com/acryldata/mcp-server-datahub/issues/192).
> - The Model Context Protocol server's `search` tool has no `Assertion` fragment in its
>   projection, so filtering a search to `entity_type = assertion` returns results stripped to
>   their bare URNs rather than the type and description that searching the same filter through
>   `searchAcrossEntities` returns, which is
>   [acryldata/mcp-server-datahub#193](https://github.com/acryldata/mcp-server-datahub/issues/193).
>   Estate wide assertion questions in the skill therefore go through the CLI on Core.
>
> The skill was written to work without any particular external tool. The one implementation it
> names, in a single clearly marked section, is [MCMR](https://github.com/phvv-me/mcmr), a code
> policy engine built for the Build with DataHub Agent Hackathon that runs the whole loop as one
> command and uses exactly the assertion identity scheme and property keys described here. It is
> referenced as a concrete example of the convention, never as a dependency, and every step of the
> loop is documented as a CLI workflow that stands on its own.
>
> ## Checks
>
> `pre-commit run --all-files` passes, which covers prettier, markdownlint-cli2, and the file
> hygiene hooks.

## Repository edits this pull request also needs

Three small integration points keep the new skill discoverable the way the other five are.

### `commands/code-guardian.md`

````markdown
---
name: code-guardian
description: Check repository code against the catalog, repair what it proves, record the verdict back
argument-hint: "[repository path or change to review]"
---

# DataHub Code Guardian

Use the Skill tool to invoke the full `datahub-code-guardian` skill:

```
Skill tool:
  skill: "datahub-skills:datahub-code-guardian"
```

**User's request:** $ARGUMENTS

This skill runs one loop over code that touches governed data:

1. Map the code to the catalog and resolve every named asset to a URN
2. Read what earlier runs already concluded about those assets, before proposing anything
3. Check the code against schema, types, ownership, tags, and lineage
4. Repair only what the catalog proves, and verify by re-running the check
5. Record every verdict back as a custom assertion

If no arguments provided, ask which repository or change to review.
````

### `skills/using-datahub/SKILL.md`

Add one row to the routing table.

```markdown
| **Check code against the catalog** (validate a pipeline, repair a rename, record a run) | **Code Guardian** | `/datahub-code-guardian` |
```

And one disambiguation rule beside the existing lineage rule.

```markdown
### Code vs. catalog questions

- **"What breaks if I change X"** → **Lineage** (catalog reachability)
- **"What breaks in this repository if X changes"** → **Code Guardian** (source joined to catalog)
- **"Record what my scan concluded about X"** → **Code Guardian** (external verdicts as custom assertions)
```

### `README.md`

A section under `Catalog interaction skills`, after Quality.

````markdown
#### Code guardian

Check repository code against the catalog that governs the data it touches. Maps source references
to assets, reads what earlier runs already concluded before proposing anything, repairs only what
column-level lineage proves, and records every verdict back as a custom assertion.

```
> Check this repo against DataHub before I merge
> What has already been tried on the orders table?
> /datahub-code-guardian the orders table dropped legacy_total, fix the pipeline
```
````

A row in the commands table.

```markdown
| `/code-guardian [path]` | Check code against the catalog and record the verdict |
```

A row in the `What works where` table.

```markdown
| Code guardian loop | Yes | Yes |
```

And the manual install list gains one line.

```bash
cp -r datahub-skills/skills/datahub-code-guardian     your-project/.agents/skills/
```

## Opening it

Everything below runs from this repository root and stops one command short of submitting. That
last command is deliberately yours to run.

```sh
gh repo fork datahub-project/datahub-skills --clone --remote=false /tmp/datahub-skills
cd /tmp/datahub-skills
git checkout -b feat/datahub-code-guardian

cp -r ~/projects/packages/mcmr/docs/contrib/datahub-skills/datahub-code-guardian skills/
```

Apply the three integration edits above by hand, since each one inserts a row or a section into an
existing file, then let their hooks format everything.

```sh
pip install pre-commit && pre-commit install
pre-commit run --all-files

git add -A
git commit -m "feat: add datahub-code-guardian skill"
git push -u origin feat/datahub-code-guardian
```

The body of the pull request is the quoted **Body** section of this file with its blockquote
prefix removed, which one command extracts.

```sh
awk '/^## Body/{f=1;next} /^## Repository edits/{f=0} f' \
  ~/projects/packages/mcmr/docs/contrib/datahub-skills/PR.md |
  sed 's/^> \{0,1\}//' > /tmp/pr-body.md
```

Read `/tmp/pr-body.md` before going further, because the extraction is a convenience rather than a
guarantee. Then the last command, which is the one that is yours to run.

```sh
gh pr create --repo datahub-project/datahub-skills \
  --title "feat: add datahub-code-guardian skill" \
  --body-file /tmp/pr-body.md
```
