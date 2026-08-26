# MCMR system

MCMR turns repository policy into typed queries. It separates source understanding, rule logic,
judgment, repair, and presentation so each boundary can be tested independently.

## Nonnegotiable properties

- One repository walk supplies one request.
- One selected fact family is extracted once.
- One rule is invoked once.
- A rule receives only the tables and services named by its signature.
- Providers retain primitive evidence and never decide a rule's verdict.
- Rules never clamp illegal provider values.
- A normal run is stateless and writes nothing unless the user requests a report or repair.
- Contextual and network work stays disabled unless explicitly enabled.
- A fix is kept only after syntax validation and a fresh rule check.

## Execution flow

```text
configuration
    |
catalog and plugin discovery
    |
selected rule signatures
    |
fact family dependency graph
    |
Rust source kernel plus enabled external providers
    |
typed repository tables
    |
one lazy query per rule
    |
policy judgment and bounded evidence
    |
Rich, plain, or JSON report
    |
optional preview or verified application
```

The planner groups rules whose table dependencies connect. Each group receives shared tables and
releases them after its queries finish. Polars collects summaries first. Detailed findings and
repair rows are collected only for retained failures.

The OpenRouter planner also groups contextual rules that read the same retained evidence. It
normalizes each claim once, packs dependency components under candidate, input, and output limits,
then restores every answer to its original rule and candidate position. Passing answers carry no
extra prose. Failed and unresolved answers retain concise reasons and their exact citations.

## Source layout

One distribution named `mcmr` ships everything, and `src` holds the three trees it is built from.

`src/core` is the Rust kernel and PyO3 extension. It owns discovery, parsing, repository graphs,
primitive evidence, and direct Polars frames.

`src/mcmr` is the Python engine, CLI, and built-in rule catalog. It owns contracts, configuration,
dependency injection, query planning, judgment, rendering, and plugin discovery, and `src/mcmr/rules`
holds every rule that needs nothing beyond the repository itself.

`src/mcmr_datahub` is the bundled DataHub plugin, and it is a plugin in the ordinary sense rather
than a privileged one. `rules/` holds the `ALL-DATA` catalog and `services/` holds the provider,
its settings, its SQL resolver, and its transports. It reaches the engine only through the public
`mcmr` imports a third-party package uses, and the engine reaches it only through the `mcmr.rules`
and `mcmr.providers` entry points below. Because one distribution ships both, the entry-point
mechanism is exercised on every install rather than only by outside packages.

The typed fact families those rules read stay in `mcmr.facts` beside every other external family.
A fact model is the engine's own legal value domain rather than a vendor schema, and a family is
owned at run time by whichever provider claims it, so a second catalog could supply `DataAssetFact`
without depending on this plugin at all.

Maturin builds that one wheel from exactly one Python source root, which is why `src` holds the
importable packages directly. This split keeps the public extension surface in Python while
measured source work remains in Rust.

## Facts and tables

A `Fact` is one independently identifiable unit of evidence. Fact models define the provider
schema and legal value domain. Constrained types make impossible counts, percentages, paths, and
identities fail at the provider boundary.

Production queries do not loop over Pydantic objects. The kernel normalizes facts into typed Polars
relations. `Table[FunctionFact]`, `Table[CallFact]`, and other table types expose those relations
without hiding collection or joins.

Rules derive conclusions from primitive columns. A provider may retain a call target, a source
span, a reference count, or a graph edge. It may not retain a field such as `should_move` that
already answers the rule.

The first table in a rule signature supplies output identities. Additional tables provide joinable
evidence. Language annotations can narrow any table before the rule runs.

## Rule declaration

Every built-in rule lives below a path shaped like the following.

```text
mcmr.rules.<scope>.<lane>.<family>.<optional groups>.rNNNN
```

The explicit identifier remains searchable. The path independently validates its scope, lane,
family, and continuous number. Duplicate identifiers and numbering gaps fail catalog construction.

```python
@rule("PY-IMPO0003", fix_safety=FixSafety.REVIEW)
def unused_import(subject: Table[ImportBindingFact]) -> OccurrenceQuery:
    frame = subject.facts()
    value = (pl.col("reference_count") == 0) & ~pl.col("is_reexported")
    return RuleQuery.boolean(
        frame,
        value,
        findings=FindingQuery.precise_boolean(frame, value, "unused import"),
    )
```

Required parameters are injected tables or explicit services. Keyword-only parameters with
defaults are user settings. A rule returns one Boolean, count, percentage, category, or contextual
query. Policy belongs to the decorator and can be overridden by project configuration.

Rule documentation is part of the contract. It states a summary, definition, evidence,
exceptions, examples, and references. Catalog tests validate the format and upstream references.

The complete rule docstring follows this page order.

```
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

Every reference line is held to the parser's own grammar.

```
(?P<url>https?://\S+)
|(?P<relation>Generalizes|Adapts|Cites) (?:"(?P<work>[^"]+)"(?:, (?P<locator>.+))?
|(?P<tool>[A-Za-z][A-Za-z0-9-]*)(?P<identity>(?: [A-Za-z0-9][\w.-]*){1,2}))
```

## Rule plugins

An installed package exposes a module or package through the `mcmr.rules` entry point group.

```toml
[project.entry-points."mcmr.rules"]
datahub = "mcmr_datahub.rules"
```

Discovery imports leaf modules in stable order. Plugin rules use the same identifiers,
documentation, typing, numbering, policy, and query validation as built-ins, so a plugin rule
module still sits at `rules.<scope>.<lane>.<family>.<optional groups>.rNNNN` below its own package
and its identifier is still checked against that path. IDs are globally unique.

A rule-only package depends on `mcmr`. Nothing else is needed, and the bundled DataHub plugin at
`src/mcmr_datahub` registers itself exactly this way rather than through a private path.

## External fact providers

An external provider owns one or more custom fact families and exposes a callable factory through
the `mcmr.providers` entry point group.

```toml
[project.entry-points."mcmr.providers"]
datahub = "mcmr_datahub.services:DataHubProvider"
```

The entry point loads a zero-argument factory. Its instance implements the structural
`FactProvider` protocol. MCMR gives each invocation a `ProviderContext` with the repository, named
settings, requested families, and only the typed tables declared by each output family.

```python
from mcmr.facts import DataAssetFact, Fact
from mcmr.plugins import ProviderContext, RepositoryTables, provider


@provider
class DataHubProvider:
    families = {DataAssetFact: set()}

    async def tables(self, context: ProviderContext) -> RepositoryTables:
        ...
```

Provider ownership is exact. Two providers cannot claim the same requested family. The `families`
mapping states each output family and only the typed inputs needed to build that output. A provider
must return every requested family it owns and no others. These dependencies form one validated
acyclic graph. Native dependencies are materialized once and reused if a rule also reads them. The
engine skips rules whose families are not available.

Provider settings live under `tool.mcmr.providers.<entry point name>`. The core treats values as
validated JSON and does not interpret vendor options. A provider chooses how to obtain secrets.

External fact classes set `external_evidence` to true. This keeps their rules out of ordinary
offline runs. The command must enable `--external` or the equivalent configuration before any
provider loads or performs network work.

The bundled DataHub plugin calls `${DATAHUB_GMS_URL}/api/graphql` directly with HTTPX. It reads an
optional bearer token from `DATAHUB_GMS_TOKEN` and retains no response cache. Its SQLGlot resolver
joins literal SQL table and field references to exact catalog identities. Ambiguous names remain
unresolved instead of becoming guesses. It also retains the exact string literal that named each
field, which is the anchor a verified repair edits, and the column the asset's own fine-grained
lineage proves replaced a retired one.

A `recorded` setting names a directory of captured exchanges instead of a live server. One JSON
file per operation holds the variables that identify a request beside the exact response envelope,
so replay is a lookup rather than a simulation and a live capture is a drop-in replacement. An
exchange states only the variables it is keyed by, which is what lets a volatile value such as a
run timestamp go unpredicted and an exchange naming none answer the whole operation. `mcmr demo`
runs the complete workflow over one such recording with no service, no network, and no edit to the
example.

## Result publication

A run that judges a governed asset knows something the next run would otherwise rediscover, so
MCMR can leave that conclusion where the asset already lives. A provider that can write a
completed run back to its own system implements `ResultPublisher` beside `FactProvider`, and one
that can read those conclusions back implements `RunHistoryReader`.

Publication is never part of reading evidence. A check reads and returns nothing of its own unless
somebody says so, which `mcmr check --writeback` does for one run and `publish_runs` does for a
scheduled one. The flag is three-valued like the execution overrides, so `--no-writeback`
suppresses recording a project already asked for.

```toml
[tool.mcmr.providers.datahub]
publish_runs = true
```

What crosses the seam is the run itself rather than a rendering of it. A `RunRecord` states one
rule's verdict about one subject, the measurement behind it, how many findings it carried, how far
its repair got, and for a contextual rule what the model said and how sure it was. Those records
come from the report the run already produced, so nothing is analyzed twice and what a provider
stores is exactly what the reader on screen was shown.

A `RunGraph` crosses the same seam beside them. A run already knows which fact families it
materialized, how many rows each carried, which columns the fact model declares, and which rule
declared which of them, so stating that graph costs no second pass. It is what gives a verdict
about ordinary source somewhere to live, because the fact table a rule queried is the closest
thing a repository has to a subject a catalog can hold.

### Where a verdict is stored

A rule that names a governed identity keeps storing its verdict there, since that asset is a
subject somebody else already owns. Every other rule anchors on the fact dataset published for the
first table in its signature. The verdict's own identity is the file and fact a finding named, so
a rule failing at two files inside one table keeps two timelines under one subject, and the file
travels with the verdict as a property. A rule that read no published table still produces no
record, which is what keeps an unanchored repository-wide verdict out of a catalog.

Nothing writes a file-scoped verdict again once that file is repaired, renamed, or deleted, so
each publication closes the ones this run no longer reports. A rule that ran knows every file it
still reports, and every earlier file of that rule receives one passing result stating that it is
no longer reported. A rule that did not run closes nothing, because silence is not a resolution.

The bundled DataHub publisher records each rule and subject pair as one custom assertion, which is
DataHub's own model for a check an external tool owns. The assertion identity is derived from the
rule identifier and what the verdict is about, so a later run lands on the same assertion instead
of creating a second one, and each run reports one result against it with the record's fields as
properties. That leaves a timeline the catalog already knows how to show and query rather than a
document only MCMR can read.

### The graph a repository publishes

The same gate publishes the graph, because a verdict has nowhere to be stored until the fact
tables exist. One dataset per fact family carries `schemaMetadata` flattened from the pydantic
fact model as dotted field paths and a `datasetProfile` stating the rows this run read. One
`DataFlow` names the repository and holds its extraction job, which outputs every fact dataset.
That is a lineage graph for source code, published into the place a data team already reads
lineage.

A rule is one thing, so it is one entity. Every rule lives as a single `DataJob` under one
canonical `mcmr/rulebook` flow for the whole instance, keyed by its identifier, rather than as a
copy under each repository that ran it. Publishing a repository reads what earlier repositories
already wrote onto that job and merges into it, so the rule's `inputDatasets` become the union of
every codebase's fact tables for the families it reads, which is what makes a rule page answer
which codebases run it. Two repositories publishing at the same moment race, and the later write
wins.

The same merge carries what each codebase currently reports, as `lastResult.<repo>`,
`findings.<repo>`, `lastRun.<repo>`, `since.<repo>` and `anchor.<repo>`, beside the
`reposFailing`, `reposPassing` and `totalFindings` rollups recomputed from the merged set. A
reader following lineage lands on the rule and reads what it concluded everywhere without opening
anything, and one link per codebase, failing first, points at the fact table its verdicts are
recorded against.

### What a contextual rule costs

A contextual rule is the only kind of rule that costs money to run, and the amount is what tells
an expensive rule apart from a cheap one that fires just as often. The backend reports its token
usage per candidate already, so that usage is kept per file rather than aggregated away, and it
travels with the run graph as the spend of the rule job that paid it. Every verdict a contextual
rule reaches then states `backend`, `model`, `reasoningEffort`, `inputTokens`, `cachedInputTokens`
and `outputTokens` for the turns behind that verdict alone, whether the rule failed or passed,
because the model was paid either way. A verdict about one file states what the turns that read
that file cost, and the repository-wide verdict states the whole rule. A batched assessment
answers every criterion in one turn and stamps that one turn on each answer, so the distinct turns
are counted rather than the answers, which is what stops one turn being billed once per criterion.
The cached input travels beside the fresh input because a harness that reuses a prompt reports
almost all of its input as cached, and a rule read as costing one token would be a lie.

The rule job rolls the same numbers up per codebase as `tokens.<repo>`, everything that rule has
cost there across its recorded timeline, and `lastRunTokens.<repo>`, what the run that just
finished cost, beside a `totalTokens` rollup across every codebase. Sorting the properties table
by that answers which rule costs the most for what it finds. A deterministic rule states none of
these keys at all rather than a row of zeroes a reader has to learn to ignore.

### The run itself

An assertion timeline answers what one rule keeps concluding. It cannot answer what a single
invocation did, because every verdict in it belongs to a different rule and a different day. Each
`mcmr check --writeback` therefore mints one run identity, `mcmr-<repository>-<epoch millis>`,
stamps it on every assertion result it reports as `runId`, and writes that same identity as one
`DataProcessInstance` whose `parentTemplate` is the repository's flow. The instance carries a
`STARTED` and a `COMPLETE` run event. A completed invocation states `SUCCESS` because policy
failures describe the code rather than an operational failure of MCMR. Those failures remain in
the instance properties and assertion results. The two events put the invocation on the flow's
own Runs tab rather than only in search.

Its properties say how much the invocation reached and what kind of work it was, as `files`,
`facts`, `failures`, `findings`, `rulesExecuted`, `rulesFailing`, one `rules<Lane>` count per lane
the run activated, `durationMillis` measured over the whole invocation rather than the query
engine alone, and, when the contextual lane ran, the backend, the model and the run's total token
usage. Reusing the identity already stamped on every verdict is what lets a reader pivot from one
rule's timeline to the invocation that wrote it and back. A run that published no fact table has
no flow to hang under, so it records no instance rather than an orphan the catalog cannot show.

What the UI calls each of these is stated rather than inferred. A fact dataset is a `Fact table`,
a repository's own job is an `Extraction`, and a rule is named by the lane it answers in, so a
search result says what it found instead of naming the generic type every platform contributes.

A rulebook of hundreds is only readable if a reader can narrow it, so a rule also carries its lane
as a coloured tag a search filters on and its family as a glossary term. The lane is two axes
rather than one, because a rule can need both a classification backend and a network, so the type
label states the stronger of them while the tags state both, and every recorded verdict carries
the same lane as a property. The family terms hang off one `MCMR Rule Families` group, which is
the taxonomy the whole catalog is browsed by. Only the lanes and families a run actually reached
are published, so no tag exists that nothing carries.

A fact dataset's schema is described from the model rather than annotated by hand. A column keeps
whatever its own field states, and a column with nothing of its own is described by the record it
belongs to, since a fact model says what each record it nests is for. A column of the fact itself
keeps none, because the dataset already carries that sentence.

None of this reaches a home page on its own, so an owner and a domain travel with everything a run
publishes. Both are settings, both default to something a fresh DataHub already knows about, and
the `Codebases` domain every published flow is filed under is the codebase registry rather than a
second mechanism beside one. The platform card carries its own mark over a public HTTPS URL,
because DataHub's web interface does not consistently render a data URI. A project that asks for
it also receives one home page post per repository, keyed by that repository so a later run
rewrites the same card.

A link nobody can follow is worse than no link. An unset or placeholder `report_url` writes no
institutional memory and no assertion `externalUrl` at all, rather than pointing a catalog at
something that answers nothing.

```toml
[tool.mcmr.providers.datahub]
publish_runs = true
report_url = "https://github.com/phvv-me/mcmr"
owner = "datahub"
domain = "Codebases"
announce = false
frontend = "http://localhost:9002"
```

GraphQL has no mutation for declaring a dataset with a schema, so this half of the publication
goes through the ingestion surface the catalog itself is loaded through, `POST /openapi/v3/entity/
<type>`, over HTTPX through the same transport seam the queries use, and reads what a shared rule
already holds back through `batchGet` on the same path. The runtime never grows an
`acryl-datahub` dependency for it. Every write is an upsert keyed by the entity URN, so a
scheduled run rewrites the same graph rather than growing a new one, and no read-before-write is
needed the way `addLink` needs one.

Assertions are declared for the whole run before any result is reported against them. DataHub
resolves an assertion through an index its own upsert reaches seconds later, so reporting in the
same breath as the upsert pays that settling window once per assertion. Declaring first spends it
on the rest of the batch, which is what keeps a repository with two hundred rules recording in
seconds rather than minutes.

Each judged asset also receives one institutional memory link through `addLink`. That aspect is
additive and editable, so a tool states what it found without overwriting a sentence a person
wrote. `updateDescription` would do the opposite, which is why an agent must not reach for it.
`addLink` refuses a link an asset already holds, so the publisher reads the existing memory first
and writes only what is missing, which is what lets a scheduled job run twice.

Two facts about the running service shape this path. A result reported against an assertion the
same run created is still rejected until that write settles, so it is reported again across a
bounded settling window rather than failing the writeback. And every optional collection in its
GraphQL schema is answered with `null` instead of an empty list when the aspect behind it was
never written, so the provider reads each one as absent rather than empty.

`mcmr history` is the other direction and the reason the first one is worth doing. It reads the
recorded verdicts for the subjects a repository names and states, per rule, whether it is passing
or failing, since when, how many repairs already landed, and why it last failed, grouped by the
warehouse asset or the fact table each timeline belongs to. An agent converging a legacy
repository reads that before it acts, so it does not spend a batch rediscovering a failure
somebody already recorded or reattempting a repair that was already refused. Naming assets
directly skips the analysis entirely, which is the fast path an agent takes. Learning which
subjects a repository names needs neither a model nor a network read the project did not already
enable, so this command runs neither lane beyond the configuration.

The official `datahub` CLI remains useful for setup and diagnostics. DataHub MCP is a separate
agent surface for targeted lineage exploration and verified writeback. It does not become the
product transport or a hidden MCMR dependency.

## Manuscripts

A paper is a program a reader executes once, from the top, with no way to jump back, and most of
what a cold reader complains about is that execution needing something it has not been given yet.
A symbol used before it is defined, a term used before it is introduced, a theorem referenced
before it is proved, a table met before anything says why it is there, one letter carrying two
meanings, a number in prose the cited table does not hold. Every one of those is a statement about
reading order and about where a thing was introduced, so the kernel establishes both once and
every rule reads that one answer.

`Manuscript::scan` reads every markup file the repository holds, finds the roots that declare a
document class, and splices each included file into the reading order at the position that
included it. What comes out is one flattened element stream per manuscript, and the element
variants are markup neutral. A LaTeX reader and a Typst reader disagree about how a heading or a
cross reference is spelled and agree about what one is, so the readers differ and the reading
order, the facts and every rule are written once. The LaTeX reader is lexical rather than a
parser, because TeX is macro expansion and has no grammar a scanner can settle, and a control
sequence it does not recognize contributes a word boundary and nothing else.

Three families come out of one walk, because a paragraph, a symbol and a number have to agree
about which section they were met in or no comparison between them means anything.
`ManuscriptFact` holds the skeleton, its sections, statements, floats, labels, references,
paragraphs and sentences. `ManuscriptNotationFact` holds what the document calls things, its
symbols, the places it appears to introduce one, the phrases it marks as terms, and the rows of
its own notation index. `ManuscriptEvidenceFact` holds the numbers it prints and the sources it
leans on, with each number retaining whether it sat in a table cell and which float held it.

Everything retained is an observation. A reference retains where it points rather than a claim
that it points forwards, a statement retains the order of whatever followed it rather than a claim
that it is unproved, and a number retains the cell it sits in rather than a claim that the prose
disagrees. Which of those is a defect is a question about one project's conventions, so it lives
in a rule and its thresholds are settings.

Nothing in this family repairs anything. A repair to code is proved by reparsing it and rerunning
the rule, and neither proof exists for prose, where a wrong repair to an argument is far harder to
see than a wrong repair to a function. The lane reports.

## Contextual rules

Contextual rules build typed candidates from local tables. The engine batches candidates and calls
one explicitly configured classification backend. A backend returns closed categories with
provenance rather than free-form findings.

A category name states what the model observed and never what the engine will do with it, so the
prompt carries the project's own outcome map beside the rule instructions. Each category is named
with what selecting it reports, drawn from the resolved policy through `Policy.reported`, and the
model is told to answer what the evidence states rather than what it would prefer to report.

The closed answer set of a contextual rule is the type argument of its `ModelQuery` return
annotation, so a policy declaration never repeats it. `Category.outcomes(good=..., neutral=...)`
names what this project accepts and tolerates, `Category.advisory()` says every answer is a
recommendation, and `@rule` closes the partition against the annotation. A named category the
annotation does not hold is refused at declaration.

Contextual execution is separate from external evidence. A local model rule needs `--contextual`.
A DataHub-backed deterministic rule needs `--external`. A DataHub-backed contextual rule needs
both.

Four backends answer that contract. `gliner2` runs local weights, `codex` and `claude` each run one
isolated schema-constrained process per bounded batch, and `openrouter` posts the same closed schema
to an OpenAI-compatible server and reads its key from `OPENROUTER_API_KEY`. Every process and HTTP
backend shares one prompt, schema, and citation protocol, so a batch reaching a new provider changes
transport alone. `mcmr model-sweep . --backend <name> --model <model>` exercises every contextual
rule through one of them without editing the project.

## Repairs

A rule declares repair safety once on `@rule`. `FixQuery` does not repeat it. Compilation rejects a
rule that declares safety without returning a fix or returns a fix without declaring safety.

`FixQuery` carries a summary and three normalized relations.

- Rewrites state typed operations such as remove, replace, move, unwrap, rename, and inline.
- Nodes retain exact source anchors used by those operations.
- Imports state bindings the rendered replacement needs.

Nodes and imports default to typed empty relations. A simple path deletion therefore supplies only
its rewrite relation.

The query selects the same `fact_id` values that produced the finding. It does not call the
provider again. The collector materializes only failed repair rows and converts them to immutable
rewrite models.

The Python renderer validates retained source and UTF-8 byte spans. It manages runtime,
`TYPE_CHECKING`, and relative imports. Cross-file moves must name an existing destination and exact
anchors. The renderer rejects stale source, overlapping edits, incomplete references, unsupported
language operations, and syntax failures.

A replacement is also read against the node it overwrites. Reparsing proves the result is Python
and rerunning the rule proves the finding closed, yet neither proves the new source still means
what the old source meant, so a rule writing a replacement out of the parts it modeled can drop a
part it never modeled. The renderer therefore compares what the replaced span supplied against what
the written span states, and refuses the plan when a value or a `*` or `**` unpacking disappears.
Names stating what the span calls, imports, or declares as a type are routes a repair may reroute,
which is why `list(values)` may become `[values]`, while the values those calls consume have to
survive. Every revised module is checked for import hygiene the same way, so a repair that would
leave one name imported twice is refused rather than written.

Safe application is transactional. MCMR writes one candidate atomically, reparses it, reruns the
originating rule, and keeps it only when the precise finding declines. Review repairs are preview
only.

Directory relocation remains intentionally stricter than a source move. A safe pathway collapse
must merge package initializers, prove collision freedom, rewrite every import and module identity,
and validate both Python and Rust module semantics. A file move without those proofs is not an
autofix.

## Configuration and state

MCMR reads configuration from `pyproject.toml`.

```toml
[tool.mcmr.execution]
deterministic = true
contextual = false
external = false

[tool.mcmr.contextual]
backend = "codex"
model = "gpt-5.6-terra"
reasoning_effort = "medium"
```

The default check constructs all requested tables in memory. It creates no `.mcmr` directory,
cache, historical report store, or evidence database. An explicitly named report is ordinary user
output rather than hidden state.

## Verification

The validation stack has distinct responsibilities.

- Rust unit tests hold parser, graph, and provider semantics.
- Focused rule tests state positive cases and documented exceptions.
- Property tests sweep complete model domains and reject impossible outputs.
- Variation ledgers fail in both directions when provider fields become constant or start varying.
- Catalog tests validate identity, numbering, documentation, policy, dependencies, and repairs.
- Oracle tests compare overlapping behavior with upstream tools.
- Coverage gates require complete statement and branch coverage.
- The self-scan runs MCMR over its own source tree.

Test volume is also analyzed as repository structure rather than accepted as a proxy for quality.
The kernel records each collected test's literal-neutral body, assertion shapes, fixture closure,
direct production calls, and transitive production reach. Rules use those relations to find exact
duplicate intent, repeated whole-graph reach, low-diversity production hotspots, broad literal
families that should become Hypothesis properties, and module-generated parametrizations that can
silently multiply collection. Findings remain review signals because static reach cannot prove that
runtime behavior, marks, or domain meaning are redundant.

The main contribution gate is the following.

```sh
chefe run contribute
```
