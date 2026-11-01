# MCMR (deprecated)

MCMR, "My Code, My Rules", is no longer developed. Its rules moved into
[mainboard](https://github.com/phvv-me/mainboard), which keeps them as SQL over code facts and runs
them with `mb code rules`:

```sh
mb code rules check     # every finding of the rules, grouped by rule
mb code rules fix       # fix what is fixable, proving each fix before keeping it
mb code lint            # fix, then check, the files that changed
mb code rules explain   # the catalog, one rule at a time
```

206 of the 301 rules are ported, 16 are left to Ruff, and the contextual (LLM) lane and the DataHub
were dropped. The ported rules live in
[`src/mainboard/analysis/rules`](https://github.com/phvv-me/mainboard/tree/main/src/mainboard/analysis/rules).

- `0.0.4` stays installable from [PyPI](https://pypi.org/project/mcmr/); no further releases are
  planned.
- The last tree with the code is this repository at commit
  [`6b86a12`](https://github.com/Pedrexus/mcmr/tree/6b86a12f02f3a890e4df2b7b93562990c8086e80), and
  its Apache-2.0
  [license](https://github.com/Pedrexus/mcmr/blob/6b86a12f02f3a890e4df2b7b93562990c8086e80/LICENSE)
  applies to it.
