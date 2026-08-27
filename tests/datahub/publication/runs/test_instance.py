import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import (
    FactColumn,
    FactDataset,
    ModelSpend,
    RuleCounts,
    RunGraph,
    RunSummary,
)
from mcmr_datahub import DataHubRunInstance, DataHubSettings
from mcmr_datahub.services.publication import flow_urn, instance_urn

from ..support import aspect

if TYPE_CHECKING:
    from collections.abc import Sequence

_RUN = "mcmr-mainboard-1786096800000"

_ANCHOR = "mainboard/facts/literal_group_fact"

_GRAPH = RunGraph(
    repository="mainboard",
    datasets=[
        FactDataset(
            family="LiteralGroupFact",
            name=_ANCHOR,
            columns=[FactColumn(path="key", native="str")],
            row_count=7,
        )
    ],
)

_SUMMARY = RunSummary(
    files=42,
    facts=310,
    failures=2,
    findings=9,
    rules=RuleCounts(executed=17, failing=2, by_lane={"deterministic": 15, "contextual": 2}),
    duration_milliseconds=1840.0,
    spend=ModelSpend(
        backend="claude",
        model="claude-sonnet-5",
        reasoning_effort="high",
        input_tokens=4000,
        cached_input_tokens=30000,
        output_tokens=250,
    ),
)

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])
_OBJECT = TypeAdapter(dict[str, JsonValue])


def recorded(
    graph: RunGraph = _GRAPH,
    summary: RunSummary = _SUMMARY,
    run: str = _RUN,
) -> tuple[list[dict[str, JsonValue]], list[str]]:
    """Run one instance publication through a mock transport and return what it posted."""
    posted: list[dict[str, JsonValue]] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        posted.extend(_ENTITIES.validate_python(json.loads(request.content)))
        return httpx.Response(200, json=[])

    async def run_publication() -> list[str]:
        settings = DataHubSettings.from_mapping(
            {"server": "https://catalog.example", "report_url": "https://runs.example/report"}
        )
        return await DataHubRunInstance(settings, httpx.MockTransport(respond)).publish(
            graph,
            summary,
            run=run,
            at=datetime(2026, 8, 8, 9, 0, tzinfo=UTC),
        )

    return posted, anyio.run(run_publication)


def events(posted: Sequence[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
    """Return the run events the two captured requests carried, in the order they were written."""
    return [aspect(entity, "dataProcessInstanceRunEvent") for entity in posted]


def test_a_recorded_run_hangs_under_the_flow_of_the_repository_it_judged() -> None:
    """A run instance with no flow above it is unreachable, so the parent travels with it."""
    posted, receipts = recorded()
    started, completed = posted
    relationships = aspect(started, "dataProcessInstanceRelationships")

    assert started["urn"] == instance_urn(_RUN) == completed["urn"]
    assert relationships == {
        "parentTemplate": flow_urn("mainboard"),
        "upstreamInstances": [],
    }
    assert receipts == [
        "mainboard recorded run mcmr-mainboard-1786096800000, "
        "17 rules and 2 failures in 1.8s for 34250 tokens"
    ]


def test_a_recorded_run_states_how_many_and_what_kind_of_rules_it_activated() -> None:
    """The run answers what one invocation did, which no single rule timeline can."""
    posted, _ = recorded()
    properties = aspect(posted[0], "dataProcessInstanceProperties")

    assert properties["name"] == _RUN
    assert properties["externalUrl"] == "https://runs.example/report"
    assert properties["created"] == {"time": 1786179598160, "actor": "urn:li:corpuser:datahub"}
    assert properties["customProperties"] == {
        "runId": _RUN,
        "repository": "mainboard",
        "files": "42",
        "facts": "310",
        "failures": "2",
        "findings": "9",
        "rulesExecuted": "17",
        "rulesFailing": "2",
        "durationMillis": "1840",
        "rulesContextual": "2",
        "rulesDeterministic": "15",
        "backend": "claude",
        "model": "claude-sonnet-5",
        "reasoningEffort": "high",
        "inputTokens": "4000",
        "cachedInputTokens": "30000",
        "outputTokens": "250",
    }


def test_a_recorded_run_opens_before_it_closes_as_a_completed_invocation() -> None:
    """Policy failures describe code and never make a completed invocation look crashed."""
    failing, clean = (
        events(recorded()[0]),
        events(
            recorded(summary=_SUMMARY.model_copy(update={"failures": 0, "spend": ModelSpend()}))[0]
        ),
    )

    assert failing[0] == {
        "timestampMillis": 1786179598160,
        "status": "STARTED",
        "attempt": 1,
    }
    assert failing[1] == {
        "timestampMillis": 1786179600000,
        "status": "COMPLETE",
        "attempt": 1,
        "durationMillis": 1840,
        "result": {"type": "SUCCESS", "nativeResultType": "mcmr"},
    }
    assert clean[1]["result"] == {"type": "SUCCESS", "nativeResultType": "mcmr"}


def test_a_run_with_no_published_flow_and_a_run_with_no_identity_record_nothing() -> None:
    """Recording is evidence-driven, so an orphan the catalog cannot show is never written."""
    assert recorded(graph=RunGraph(repository="mainboard")) == ([], [])
    assert recorded(run="") == ([], [])


def test_a_run_that_asked_no_model_says_nothing_about_a_model() -> None:
    """A deterministic invocation states no backend, because there was none to state."""
    computed = _SUMMARY.model_copy(update={"spend": ModelSpend()})
    posted, receipts = recorded(summary=computed)
    properties = _OBJECT.validate_python(
        aspect(posted[0], "dataProcessInstanceProperties")["customProperties"]
    )

    assert "backend" not in properties and "inputTokens" not in properties
    assert receipts == [
        "mainboard recorded run mcmr-mainboard-1786096800000, 17 rules and 2 failures in 1.8s"
    ]
