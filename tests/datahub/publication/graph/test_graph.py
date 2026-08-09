import json
from pathlib import Path
from urllib.parse import quote

import anyio
import httpx
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import (
    PublicationContext,
    RuleJob,
    RuleTimeline,
    RunRecord,
)
from mcmr_datahub import DataHubOpenAPI, DataHubProvider, DataHubSettings
from mcmr_datahub.services.publication import (
    codebase_urn,
    dataset_urn,
    domain_urn,
    flow_urn,
    job_urn,
    owner_urn,
    rule_urn,
)

from ..support import aspect, emitted, properties, report_url, run_graph, table, timeline

_ANCHOR = table()

_QUOTED = quote(dataset_urn(_ANCHOR), safe="")

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])
_OBJECT = TypeAdapter(dict[str, JsonValue])


def test_a_published_fact_dataset_states_its_columns_and_the_rows_this_run_read() -> None:
    """The schema comes from the fact model and the profile from the table the run built."""
    entities, receipts = emitted("publish")
    dataset = entities["dataset"][0]

    assert receipts == [
        "chefe published 1 fact datasets as 28 entities owned by datahub in Codebases"
    ]
    assert dataset["urn"] == dataset_urn(_ANCHOR)
    assert aspect(dataset, "datasetProfile")["rowCount"] == 7
    assert aspect(dataset, "schemaMetadata")["fields"] == [
        {
            "fieldPath": "key",
            "nativeDataType": "str",
            "description": "",
            "type": {"type": {"com.linkedin.schema.StringType": {}}},
        }
    ]


def test_everything_published_carries_the_owner_and_domain_a_reader_browses_by() -> None:
    """A catalog entity nobody owns and nothing files reaches no home page section."""
    entities, _ = emitted("publish", owner="pedro", domain="Repositories")
    dataset, flow = entities["dataset"][0], entities["dataflow"][0]
    parent, child = entities["domain"]

    assert aspect(dataset, "domains")["domains"] == [codebase_urn("chefe")]
    assert aspect(flow, "domains")["domains"] == [codebase_urn("chefe")]
    assert aspect(flow, "ownership")["owners"] == [
        {"owner": "urn:li:corpuser:pedro", "type": "TECHNICAL_OWNER"}
    ]
    assert aspect(parent, "domainProperties")["name"] == "Repositories"
    assert parent["urn"] == domain_urn("Repositories")
    assert child["urn"] == codebase_urn("chefe")
    assert aspect(child, "domainProperties")["parentDomain"] == domain_urn("Repositories")


def test_the_platform_card_carries_its_own_mark() -> None:
    """DataHub reads the public package mark from a cacheable HTTPS image source."""
    entities, _ = emitted("publish")
    stated = aspect(entities["dataplatform"][0], "dataPlatformInfo")
    logo = stated["logoUrl"]

    assert logo == "https://raw.githubusercontent.com/phvv-me/mcmr/main/docs/assets/icon.png"
    assert stated["displayName"] == "MCMR"


def test_a_published_rule_job_reads_exactly_the_tables_its_signature_declared() -> None:
    """One extraction job writes every fact table, and each rule job reads the ones it named."""
    entities, receipts = emitted("summarize", [timeline("ALL-DUPL0005")])
    extraction, rule_job = entities["datajob"]
    lineage = "dataJobInputOutput"

    assert receipts == [
        "chefe merged into 1 rules of the MCMR Rulebook, 0 passing and 1 failing here"
    ]
    assert aspect(extraction, lineage)["outputDatasets"] == [dataset_urn(_ANCHOR)]
    assert aspect(rule_job, lineage)["inputDatasets"] == [dataset_urn(_ANCHOR)]
    assert rule_job["urn"] == rule_urn("ALL-DUPL0005")
    assert extraction["urn"] == job_urn("chefe", job="extract")


def test_a_rule_job_states_the_verdict_its_own_timeline_reached() -> None:
    """A reader following lineage lands on the rule, so the rule says what it concluded."""
    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005")])
    stated = properties(entities["datajob"][1])

    assert stated["lastResult.chefe"] == "FAILURE"
    assert stated["findings.chefe"] == "2"
    assert stated["since.chefe"] == "2026-08-07T09:34:00+00:00"
    assert stated["anchor.chefe"] == _ANCHOR
    assert (stated["reposFailing"], stated["reposPassing"], stated["totalFindings"]) == (
        "1",
        "0",
        "2",
    )


def test_a_contextual_rule_job_states_what_it_has_cost_and_what_its_last_run_cost() -> None:
    """Sorting a rulebook by tokens is what answers which rule is expensive rather than noisy."""
    billed = {"inputTokens": "900", "outputTokens": "100"}
    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005", billed=billed)])
    stated = properties(entities["datajob"][1])

    assert stated["tokens.chefe"] == "2000"
    assert stated["lastRunTokens.chefe"] == "1000"
    assert stated["totalTokens"] == "2000"


def test_a_deterministic_rule_job_grows_no_cost_properties_at_all() -> None:
    """A rule nobody paid for states nothing, so the properties table stays worth reading."""
    stated = properties(emitted("summarize", [timeline("ALL-DUPL0005")])[0]["datajob"][1])

    assert "tokens.chefe" not in stated and "lastRunTokens.chefe" not in stated
    assert "totalTokens" not in stated


def test_a_rule_is_summarized_by_the_timeline_that_closes_when_the_whole_rule_does() -> None:
    """One rule keeps a timeline per reported file beside the repository-wide one."""
    located = timeline("ALL-DUPL0005", where="src/orders.py", runs=3)
    entities, _ = emitted("summarize", [located, timeline("ALL-DUPL0005")])

    assert properties(entities["datajob"][1])["findings.chefe"] == "2"


def test_a_rule_job_points_at_the_fact_table_its_verdicts_are_recorded_against() -> None:
    """The verdicts are one hop away on the dataset, so the job carries the link to them."""
    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005")], frontend="https://ui.example")
    held = aspect(entities["datajob"][1], "institutionalMemory")["elements"]

    assert held == [
        {
            "url": f"https://ui.example/dataset/{_QUOTED}/Validation",
            "description": "Verdict history.chefe",
            "createStamp": {"time": 0, "actor": "urn:li:corpuser:datahub"},
        }
    ]
    assert "institutionalMemory" not in entities["datajob"][0]

    unread = run_graph().model_copy(update={"jobs": [RuleJob(rule="ALL-DUPL0005")]})
    plain, _ = emitted("summarize", graph=unread)

    assert "institutionalMemory" not in plain["datajob"][1]


def test_a_timeline_nothing_was_ever_recorded_against_summarizes_nothing() -> None:
    """A rule with no recorded run states no verdict rather than an invented one."""
    empty = RuleTimeline(rule="ALL-DUPL0005", subject=dataset_urn(_ANCHOR))
    entities, receipts = emitted("summarize", [empty])

    assert "0 passing and 0 failing" in receipts[0]
    assert "lastResult.chefe" not in properties(entities["datajob"][1])


def test_the_ingestion_client_owns_its_pool_from_construction() -> None:
    """Nothing has to be opened first, and leaving the block is what closes the pool."""

    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async def publish() -> tuple[int, bool]:
        stated = DataHubSettings(server="https://catalog.example")
        openapi = DataHubOpenAPI(stated, httpx.MockTransport(respond))
        written = await openapi.ingest("dataset", [{"urn": "one"}])
        async with openapi:
            await openapi.read("datajob", [])
        return written, openapi.client.is_closed

    assert anyio.run(publish) == (1, True)


def test_a_large_repository_is_ingested_in_bounded_requests() -> None:
    """One repository's rule jobs are many, and nothing is posted when there are none."""
    sizes: list[int] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        sizes.append(len(_ENTITIES.validate_python(json.loads(request.content))))
        return httpx.Response(200, json=[])

    async def ingest() -> tuple[int, int]:
        stated = DataHubSettings(server="https://catalog.example")
        async with DataHubOpenAPI(stated, httpx.MockTransport(respond)) as openapi:
            nothing = await openapi.ingest("datajob", [])
            many: list[JsonValue] = [{"urn": str(item)} for item in range(120)]
            return nothing, await openapi.ingest("datajob", many)

    assert anyio.run(ingest) == (0, 120)
    assert sizes == [50, 50, 20]


def test_a_run_that_consumed_no_table_publishes_no_graph(tmp_path: Path) -> None:
    """Nothing is posted for a run with no fact tables, which is what a bare record is."""
    context = PublicationContext(
        repository=tmp_path,
        settings={"server": "https://catalog.example", "report_url": report_url()},
        records=[RunRecord(rule="ALL-DUPL0005", subject=_ANCHOR)],
    )

    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"dataset": None}})

    receipts = anyio.run(DataHubProvider(httpx.MockTransport(respond)).publish, context)

    assert not any("published" in receipt for receipt in receipts)
    assert owner_urn("urn:li:corpGroup:data") == "urn:li:corpGroup:data"
    assert flow_urn("chefe") == "urn:li:dataFlow:(mcmr,chefe,PROD)"


def test_a_rule_keeps_every_codebase_that_already_published_it() -> None:
    """A rule is one entity, so a second repository is merged onto it rather than replacing it."""
    earlier: JsonValue = {
        "urn": rule_urn("ALL-DUPL0005"),
        "dataJobInputOutput": {
            "value": {"inputDatasets": [dataset_urn("other/facts/literal_group_fact")]}
        },
        "dataJobInfo": {
            "value": {
                "customProperties": {
                    "lastResult.other": "FAILURE",
                    "findings.other": "3",
                    "anchor.other": "other/facts/literal_group_fact",
                }
            }
        },
    }

    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005")], held=[earlier])
    rule = entities["datajob"][1]
    stated = properties(rule)

    assert aspect(rule, "dataJobInputOutput")["inputDatasets"] == [
        dataset_urn(_ANCHOR),
        dataset_urn("other/facts/literal_group_fact"),
    ]
    assert stated["lastResult.other"] == "FAILURE"
    assert stated["lastResult.chefe"] == "FAILURE"
    assert (stated["reposFailing"], stated["totalFindings"]) == ("2", "5")


def test_a_rule_links_the_codebases_that_are_failing_it_first() -> None:
    """The verdicts live per repository, so the link a reader wants first is the failing one."""
    earlier: JsonValue = {
        "urn": rule_urn("ALL-DUPL0005"),
        "dataJobInfo": {
            "value": {
                "customProperties": {
                    "lastResult.aaa": "SUCCESS",
                    "anchor.aaa": "aaa/facts/literal_group_fact",
                }
            }
        },
    }

    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005")], held=[earlier])
    held = aspect(entities["datajob"][1], "institutionalMemory")["elements"]

    assert isinstance(held, list)
    assert [_OBJECT.validate_python(item)["description"] for item in held] == [
        "Verdict history.chefe",
        "Verdict history.aaa",
    ]
