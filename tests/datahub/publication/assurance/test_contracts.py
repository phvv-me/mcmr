import json
from typing import TYPE_CHECKING

import anyio
import httpx

from mcmr.plugins import RunGraph, RunRecord, RunState
from mcmr_datahub import DataHubContracts, DataHubGraphQL, DataHubSettings
from mcmr_datahub.services.publication import assertion_urn, contract_id, dataset_urn

from ..support import run_graph, table

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic import JsonValue

_TABLE = table()

_GRAPH = run_graph()

_JUDGED = [
    RunRecord(rule="ALL-DUPL0005", subject=_TABLE, state=RunState.FAILURE),
    RunRecord(rule="ALL-DUPL0005", subject=_TABLE, path="src/orders.py", identity="src/orders.py"),
    RunRecord(rule="ALL-CALL0001", subject=_TABLE),
    RunRecord(rule="ALL-DATA0002", subject="urn:li:dataset:(snowflake,orders,PROD)"),
]


def upserted(
    graph: RunGraph = _GRAPH,
    records: Sequence[RunRecord] = tuple(_JUDGED),
) -> tuple[list[JsonValue], list[str]]:
    """Run one contract publication through a mock transport and return what it asked for."""
    asked: list[JsonValue] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        asked.append(json.loads(request.content)["variables"])
        return httpx.Response(200, json={"data": {"upsertDataContract": {"urn": "urn:li:x"}}})

    async def publish() -> list[str]:
        settings = DataHubSettings(server="https://catalog.example")
        async with DataHubGraphQL(settings, httpx.MockTransport(respond)) as gateway:
            return await DataHubContracts(gateway).publish(graph, list(records))

    return asked, anyio.run(publish)


def test_a_published_fact_table_is_held_to_the_rules_that_judged_the_whole_of_it() -> None:
    """A contract answers what a table promises, which a hundred timelines never say outright."""
    asked, receipts = upserted()

    assert receipts == ["chefe contracted 1 fact tables on 2 rule clauses"]
    assert asked == [
        {
            "entity": dataset_urn(_TABLE),
            "id": contract_id(_TABLE),
            "quality": [
                {"assertionUrn": assertion_urn(_JUDGED[2])},
                {"assertionUrn": assertion_urn(_JUDGED[0])},
            ],
        }
    ]


def test_a_verdict_about_one_file_stays_out_of_what_the_whole_table_promises() -> None:
    """A rule reporting one file keeps its own timeline, and the contract stays about the table."""
    asked, _ = upserted()
    clauses = asked[0]

    assert isinstance(clauses, dict)
    assert assertion_urn(_JUDGED[1]) not in json.dumps(clauses)


def test_the_contract_key_is_the_table_so_a_later_run_updates_the_same_contract() -> None:
    """A second run has to land on the first contract rather than stack another beside it."""
    assert contract_id(_TABLE) == "mcmr-chefe-facts-literal-group-fact"
    assert contract_id("chefe/facts/other") != contract_id(_TABLE)


def test_a_table_no_rule_judged_whole_is_promised_nothing() -> None:
    """A contract with no clause promises nothing, so it is never written at all."""
    located = [record for record in _JUDGED if record.path]

    assert upserted(records=located) == ([], [])
    assert upserted(graph=RunGraph(repository="chefe")) == ([], [])
