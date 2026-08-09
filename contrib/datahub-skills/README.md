# Upstream skill contribution

This directory holds a complete DataHub Skill, written in the layout and house style of
[datahub-project/datahub-skills](https://github.com/datahub-project/datahub-skills), ready to be
copied into that repository and opened as a pull request. Nothing here has been submitted.

```
datahub-code-guardian/
├── SKILL.md
├── README.md
├── references/
│   ├── catalog-read-reference.md
│   ├── assertion-history-reference.md
│   └── verdict-writeback-reference.md
└── templates/
    └── guardian-report.template.md
```

`PR.md` is the pull request title and body, plus the three repository level edits a new skill needs
so it is discoverable the way the existing five are, which are a command file, a routing row, and a
README section.

## What the skill teaches

The workflow MCMR exists to run, written so it is useful to an agent that has never heard of MCMR.
Map repository code to catalog assets, read the assertion history on those assets before proposing
anything, check the code against schema, types, ownership, tags and lineage, repair only what
column-level lineage proves, verify the repair by re-running the check, and record every verdict
back as a custom assertion so the next agent inherits the conclusion.

The skill hands the read steps off to DataHub's own skills and its Model Context Protocol server
the way those five hand off to each other, and it names MCMR once, in a clearly marked section, as
one implementation of the check, repair and record step rather than as a dependency.

## Submitting it

`PR.md` ends with an **Opening it** section that carries the whole sequence, from `gh repo fork`
through `pre-commit run --all-files` to the single `gh pr create` that is deliberately left for a
person to run. The pull request title is enforced by their `Lint PR Title` check and becomes the
squash-merge commit message, so it has to stay the Conventional Commit line that file states.

Everything here already passes prettier and markdownlint-cli2 under that repository's own
configuration, so their hooks should have nothing to say about it.
