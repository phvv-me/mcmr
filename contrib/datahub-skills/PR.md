# Pull request draft: datahub-code-guardian

Ready to open, not opened. Target repository `datahub-project/datahub-skills`, branch off `main`.

The title matters, since the repository squash merges and enforces Conventional Commits through the `Lint PR Title` check. A new skill is a feature.

```
feat: add datahub-code-guardian skill
```

## Body

This is the body now live on the open pull request,
[datahub-project/datahub-skills#112](https://github.com/datahub-project/datahub-skills/pull/112).

> ## What this adds
>
> `datahub-code-guardian`, a sixth catalog interaction skill for the moment the other five stop short of. The existing skills read and curate the catalog. This one is for when a person or an agent is about to change code that touches governed data, a pipeline, a dbt model, a query string sitting in application source.
>
> ## The problem it solves
>
> Two systems each hold half the answer. A renamed column is the cheapest change to make in the warehouse and one of the most expensive to discover in code, because the breakage lives in a query string where no type checker looks and no test fails until the overnight run. DataHub knows the column moved. The repository knows which line still reads the old name. This skill joins them before the edit lands.
>
> It also gives agents a memory. A session's context dies with it, so the next agent reopens settled decisions and reattempts repairs that were already refused for a good reason. DataHub already has the right durable store for this, custom assertions with stable urns accumulate a queryable timeline on Core. The skill reads that history before proposing anything and writes its own verdict back when it is done.
>
> ## The loop
>
> 1. Map the code to catalog assets
> 2. Read what earlier runs already concluded, before proposing anything
> 3. Check the code against schema, types, ownership, tags and lineage
> 4. Repair only what the catalog proves, and rerun the check
> 5. Record every verdict back, passes included
>
> The judgment lives in move 4. Column level lineage naming exactly one surviving field licenses a rewrite. A similar looking name does not, and the skill reports it without offering a patch.
>
> ## What is in the box
>
> - `skills/datahub-code-guardian/` with SKILL.md, a README, three references and a report template
> - `commands/code-guardian.md`
> - a routing row and disambiguation rules in `using-datahub`, plus the matching README rows
>
> Everything runs on DataHub Core through `datahub graphql` and `datahub search`, or through the Model Context Protocol server where one is connected. No external tool required. It hands off to Search, Lineage, Enrich, Quality and Setup rather than duplicating them.
>
> ## Reviewer notes
>
> Every reference was exercised against a live Core 1.6.0 instance rather than written from memory. Doing that surfaced two `mcp-server-datahub` issues, filed with reproductions as acryldata/mcp-server-datahub#192 and acryldata/mcp-server-datahub#193, and the skill routes around both on Core. One clearly marked section names [MCMR](https://github.com/phvv-me/mcmr) as a concrete implementation of the assertion conventions described here, an example rather than a dependency.
>
> `pre-commit run --all-files` passes.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)

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

cp -r ~/projects/packages/mcmr/contrib/datahub-skills/datahub-code-guardian skills/
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
  ~/projects/packages/mcmr/contrib/datahub-skills/PR.md |
  sed 's/^> \{0,1\}//' > /tmp/pr-body.md
```

Read `/tmp/pr-body.md` before going further, because the extraction is a convenience rather than a
guarantee. Then the last command, which is the one that is yours to run.

```sh
gh pr create --repo datahub-project/datahub-skills \
  --title "feat: add datahub-code-guardian skill" \
  --body-file /tmp/pr-body.md
```
