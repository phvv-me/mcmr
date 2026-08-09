from pathlib import Path

from mcmr.checking.graph import RunGraphBuilder, fact_columns
from mcmr.commands.quality import RunPublication
from mcmr.domain.contracts import Finding, ModelProvenance
from mcmr.facts import CallFact, CIConfigurationFact, Expression, SourceSpan
from mcmr.plugins import (
    ColumnType,
    FactColumn,
    FactDataset,
    ModelSpend,
    RuleJob,
    RuleTables,
    RunGraph,
    RunState,
)
from mcmr.presentation.reports import CheckReport, RuleFailure, RulePass

_ANCHOR = "chefe/facts/literal_group_fact"

_GRAPH = RunGraph(
    repository="chefe",
    datasets=[
        FactDataset(
            family="LiteralGroupFact",
            name=_ANCHOR,
            description="Retain repeated literals.",
            columns=[FactColumn(path="key", data_type=ColumnType.STRING, native="str")],
            row_count=7,
        )
    ],
    jobs=[
        RuleJob(
            rule="ALL-DUPL0005",
            callable="mcmr.rules.general.deterministic.duplication.values.r0005.repeated",
            summary="Find one string literal a single module writes out over and over.",
            tables=RuleTables(inputs=[_ANCHOR], primary=_ANCHOR),
        )
    ],
)


def failing(*paths: str) -> CheckReport:
    """Return one report whose only failure names source files and no governed asset."""
    return CheckReport(
        root=".",
        failures=[
            RuleFailure(
                rule="ALL-DUPL0005",
                summary="Find one string literal a single module writes out over and over.",
                where="src/chefe/manifest.py",
                span=SourceSpan(path=paths[0]),
                value=1,
                allowed="<= 0",
                findings=[
                    Finding(message=f"`audit` is written 4 times in {path}", span=span)
                    for path in paths
                    if (span := SourceSpan(path=path))
                ],
            )
        ],
        passes=[RulePass(rule="ALL-CALL0001", summary="Report an unresolved call.")],
    )


def test_a_verdict_about_source_anchors_on_the_fact_table_its_rule_read() -> None:
    """A rule naming no governed asset still has a subject, which is the table it queried."""
    records = RunPublication(report=failing("a.py", "b.py"), graph=_GRAPH).records

    failures = [record for record in records if record.state is RunState.FAILURE]
    assert {record.subject for record in failures} == {_ANCHOR}
    assert [record.path for record in failures] == ["", "a.py", "b.py"]
    assert failures[1].identity == "a.py src/chefe/manifest.py"
    assert failures[1].properties["path"] == "a.py"
    assert (failures[0].finding_count, failures[1].finding_count) == (2, 1)


def test_a_rule_that_read_no_published_table_records_nothing() -> None:
    """A verdict with nowhere to be stored is not given a home, it is simply not recorded."""
    assert RunPublication(report=failing("a.py")).records == []


def test_a_passing_rule_states_its_verdict_on_every_subject_it_could_have_named() -> None:
    """A pass is a conclusion, so it lands on the assets it judged and on its own fact table."""
    passing = RuleJob(
        rule="ALL-CALL0001",
        tables=RuleTables(inputs=["chefe/facts/call_fact"], primary="c"),
    )
    graph = _GRAPH.model_copy(update={"jobs": [*_GRAPH.jobs, passing]})

    records = RunPublication(report=failing("a.py"), graph=graph).records

    assert [record.subject for record in records if record.state is RunState.SUCCESS] == ["c"]
    assert (graph.anchor("ALL-CALL0001"), graph.anchor("ALL-NONE0001")) == ("c", "")


def _contextual() -> RunGraph:
    """Return one graph whose contextual rule paid a backend at each file it read."""
    estimated = RuleJob(
        rule="ALL-DESI1001",
        tables=RuleTables(inputs=[_ANCHOR], primary=_ANCHOR),
        lanes=["contextual", "external"],
        spend={
            "a.py": ModelSpend(
                backend="claude",
                model="claude-sonnet-5",
                reasoning_effort="high",
                input_tokens=900,
                cached_input_tokens=8000,
                output_tokens=100,
            ),
            "b.py": ModelSpend(
                backend="claude",
                model="claude-sonnet-5",
                reasoning_effort="high",
                input_tokens=300,
                cached_input_tokens=2000,
                output_tokens=50,
            ),
        },
    )
    computed = _GRAPH.jobs[0].model_copy(update={"lanes": ["deterministic"]})
    return _GRAPH.model_copy(update={"jobs": [computed, estimated]})


def test_a_contextual_verdict_states_what_the_turns_behind_it_cost() -> None:
    """A verdict about one file was reached by the turns that read that file, and says so."""
    graph = _contextual()

    whole, located = graph.spend("ALL-DESI1001"), graph.spend("ALL-DESI1001", path="a.py")

    assert (whole.input_tokens, whole.cached_input_tokens, whole.tokens) == (1200, 10000, 11350)
    assert located.properties == {
        "backend": "claude",
        "model": "claude-sonnet-5",
        "reasoningEffort": "high",
        "inputTokens": "900",
        "cachedInputTokens": "8000",
        "outputTokens": "100",
    }
    assert graph.spend("ALL-DESI1001", path="absent.py").properties == {}
    assert graph.spend("ALL-NONE0001").properties == {}
    assert graph.spent.tokens == 11350


def test_a_deterministic_rule_states_no_cost_at_all_rather_than_a_row_of_zeroes() -> None:
    """A rule nobody paid for grows no properties, which is what keeps the table readable."""
    computed = _GRAPH.jobs[0]

    assert computed.spent == ModelSpend()
    assert computed.spent.properties == {}
    assert _GRAPH.spent.properties == {}
    assert ModelSpend.of([ModelSpend(input_tokens=3)]).properties == {}


def test_one_batch_turn_is_billed_once_however_many_answers_carry_it() -> None:
    """Its identity travels with the counts, so the first named part names the whole sum."""
    turn = ModelProvenance(
        backend="claude",
        model="claude-sonnet-5",
        reasoning_effort="high",
        input_tokens=400,
        output_tokens=60,
    )

    combined = ModelSpend.of([turn, turn.model_copy(update={"output_tokens": 40})])

    assert (combined.model, combined.input_tokens, combined.output_tokens) == (
        "claude-sonnet-5",
        800,
        100,
    )


def test_a_run_summary_states_how_much_the_whole_invocation_reached() -> None:
    """A rule timeline cannot answer what one invocation did, so the run states it itself."""
    graph = _contextual()

    summary = RunPublication(
        report=failing("a.py"),
        graph=graph,
        elapsed_milliseconds=1840.4,
    ).summary

    assert graph.lane_counts == {"deterministic": 1, "contextual": 1, "external": 1}
    assert summary.properties == {
        "files": "0",
        "facts": "0",
        "failures": "1",
        "findings": "1",
        "rulesExecuted": "0",
        "rulesFailing": "1",
        "durationMillis": "1840",
        "rulesContextual": "1",
        "rulesDeterministic": "1",
        "rulesExternal": "1",
        "backend": "claude",
        "model": "claude-sonnet-5",
        "reasoningEffort": "high",
        "inputTokens": "1200",
        "cachedInputTokens": "10000",
        "outputTokens": "150",
    }


def test_a_contextual_verdict_carries_its_cost_whether_it_failed_or_passed() -> None:
    """The model was paid whichever way the rule answered, so a pass states the cost too."""
    graph = _contextual()
    report = failing("a.py").model_copy(
        update={"passes": [RulePass(rule="ALL-DESI1001", summary="Estimate the design.")]}
    )

    records = RunPublication(report=report, graph=graph).records

    passing = next(record for record in records if record.state is RunState.SUCCESS)
    computed = next(record for record in records if record.rule == "ALL-DUPL0005")
    assert passing.properties["inputTokens"] == "1200"
    assert passing.properties["model"] == "claude-sonnet-5"
    assert "inputTokens" not in computed.properties
    assert "backend" not in computed.properties


def test_one_fact_model_flattens_into_the_dotted_columns_a_schema_shows() -> None:
    """Nested records become dotted paths, and a model reachable from itself stops the walk."""
    columns = {column.path: column for column in fact_columns(CallFact)}

    assert columns["span.start_line"].data_type is ColumnType.NUMBER
    assert columns["calls.is_external"].data_type is ColumnType.BOOLEAN
    assert columns["calls.arguments.literal_kind"].data_type is ColumnType.STRING
    assert columns["calls.arguments.arguments"].native == Expression.__name__
    assert "calls.arguments.arguments.text" not in columns


def test_a_fact_family_is_published_under_its_own_readable_name() -> None:
    """An acronym stays one word, which is what keeps `CIConfigurationFact` readable."""
    builder = RunGraphBuilder(Path("/tmp/chefe"))

    assert builder.family_slug(CIConfigurationFact) == "ci_configuration_fact"
    assert builder.dataset_name(CallFact) == "chefe/facts/call_fact"
    assert builder.graph().repository == "chefe"


def test_a_fact_family_is_grouped_by_the_directory_it_is_already_defined_in() -> None:
    """The taxonomy a reader browses by is where the model lives rather than a second list."""
    builder = RunGraphBuilder(Path("/tmp/chefe"))

    assert builder.family_category(CIConfigurationFact) == "structure"
    assert builder.family_category(RunGraph) == ""
