from pathlib import Path

from mcmr.checking.graph import RunGraphBuilder, fact_columns
from mcmr.commands.quality import RunPublication
from mcmr.domain.contracts import Finding
from mcmr.facts import CallFact, CIConfigurationFact, Expression, SourceSpan
from mcmr.plugins import (
    ColumnType,
    FactColumn,
    FactDataset,
    RuleJob,
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
            inputs=[_ANCHOR],
            primary=_ANCHOR,
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
    passing = RuleJob(rule="ALL-CALL0001", inputs=["chefe/facts/call_fact"], primary="c")
    graph = _GRAPH.model_copy(update={"jobs": [*_GRAPH.jobs, passing]})

    records = RunPublication(report=failing("a.py"), graph=graph).records

    assert [record.subject for record in records if record.state is RunState.SUCCESS] == ["c"]
    assert (graph.anchor("ALL-CALL0001"), graph.anchor("ALL-NONE0001")) == ("c", "")


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
