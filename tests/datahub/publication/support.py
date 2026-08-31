import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import (
    FactColumn,
    FactDataset,
    RuleJob,
    RuleTables,
    RuleTimeline,
    RunEvent,
    RunGraph,
    RunState,
)
from mcmr_datahub import DataHubCodeGraph, DataHubSettings
from mcmr_datahub.services.publication import dataset_urn

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_REPORT = "https://example.invalid/run"

_ANCHOR = "mainboard/facts/literal_group_fact"

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])
_OBJECT = TypeAdapter(dict[str, JsonValue])


def table() -> str:
    """Return the one fact table every publication test states its graph about."""
    return _ANCHOR


def report_url() -> str:
    """Return the run report a publication test links its verdicts to."""
    return _REPORT


def run_graph(category: str = "") -> RunGraph:
    """Return the one table and one rule graph a publication test publishes.

    The fact group is stated only by the tests that read a taxonomy, so a test about lineage is
    never quietly reading a tag it never asked for.
    """
    return RunGraph(
        repository="mainboard",
        datasets=[
            FactDataset(
                family="LiteralGroupFact",
                name=_ANCHOR,
                category=category,
                columns=[FactColumn(path="key", native="str")],
                row_count=7,
            )
        ],
        jobs=[
            RuleJob(
                rule="ALL-DUPL0005",
                tables=RuleTables(inputs=[_ANCHOR], primary=_ANCHOR),
                lanes=["deterministic"],
                family="duplication",
            )
        ],
    )


_GRAPH = run_graph()


def aspect(entity: Mapping[str, JsonValue], name: str) -> dict[str, JsonValue]:
    """Return the value of one aspect a captured ingestion request carried."""
    return _OBJECT.validate_python(_OBJECT.validate_python(entity[name])["value"])


def properties(entity: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Return the custom properties one captured rule job carried."""
    return _OBJECT.validate_python(aspect(entity, "dataJobInfo")["customProperties"])


def settings(**stated: JsonValue) -> DataHubSettings:
    """Return one settings object with the writeback options a test states."""
    return DataHubSettings.from_mapping(
        {"server": "https://catalog.example", "report_url": _REPORT, **stated}
    )


def emitted(
    call: str,
    timelines: Sequence[RuleTimeline] = (),
    graph: RunGraph = _GRAPH,
    held: Sequence[JsonValue] = (),
    **stated: JsonValue,
) -> tuple[dict[str, list[dict[str, JsonValue]]], list[str]]:
    """Run one publication step through a mock transport and return what it posted."""
    posted: dict[str, list[dict[str, JsonValue]]] = {}

    async def respond(request: httpx.Request) -> httpx.Response:
        entity = request.url.path.rsplit("/", 1)[1]
        if entity == "batchGet":
            return httpx.Response(200, json=list(held))
        posted[entity] = _ENTITIES.validate_python(json.loads(request.content))
        return httpx.Response(200, json=[])

    async def run() -> list[str]:
        emitter = DataHubCodeGraph(settings(**stated), httpx.MockTransport(respond))
        if call == "publish":
            return await emitter.publish(graph)
        return await emitter.summarize(graph, timelines)

    return posted, anyio.run(run)


def timeline(
    rule: str,
    *,
    where: str = "",
    runs: int = 2,
    billed: Mapping[str, str] | None = None,
) -> RuleTimeline:
    """Return one recorded timeline stating a failing rule at an optional file."""
    moment = datetime(2026, 8, 7, 9, 34, tzinfo=UTC)
    return RuleTimeline(
        rule=rule,
        subject=dataset_urn(_ANCHOR),
        events=[
            RunEvent(
                at=moment.replace(minute=34 + item),
                state=RunState.FAILURE,
                properties={"findings": str(item + 1), "path": where} | dict(billed or {}),
            )
            for item in range(runs)
        ],
    )
