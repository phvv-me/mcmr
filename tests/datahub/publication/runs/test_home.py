import json

import anyio
import httpx
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import FactDataset, RuleJob, RuleTables, RunGraph
from mcmr_datahub import DataHubAnnouncement, DataHubSettings
from mcmr_datahub.services.publication import domain_urn

_GRAPH = RunGraph(
    repository="mainboard",
    datasets=[FactDataset(family="LiteralGroupFact", name="mainboard/facts/literal_group_fact")],
    jobs=[
        RuleJob(
            rule="ALL-DUPL0005",
            tables=RuleTables(primary="mainboard/facts/literal_group_fact"),
        )
    ],
)

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])


def announced(**stated: JsonValue) -> tuple[list[dict[str, JsonValue]], list[str]]:
    """Announce one published graph through a mock transport and return what it posted."""
    posted: list[dict[str, JsonValue]] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        posted.extend(_ENTITIES.validate_python(json.loads(request.content)))
        return httpx.Response(200, json=[])

    async def run() -> list[str]:
        settings = DataHubSettings.from_mapping({"server": "https://catalog.example", **stated})
        return await DataHubAnnouncement(settings, httpx.MockTransport(respond)).publish(_GRAPH)

    return posted, anyio.run(run)


def test_a_project_that_asked_for_no_card_gets_none() -> None:
    """A home page post is somebody's front page, so nothing writes one without being asked."""
    assert announced() == ([], [])


def test_one_repository_keeps_one_home_page_card_across_every_run() -> None:
    """The card is keyed by the repository it announces, so a later run rewrites that same one."""
    posted, receipts = announced(announce=True)
    stated = TypeAdapter(dict[str, JsonValue]).validate_python(posted[0]["postInfo"])

    assert posted[0]["urn"] == "urn:li:post:mcmr-mainboard"
    assert receipts == ["mainboard announced on the DataHub home page"]
    assert stated["value"] == {
        "type": "HOME_PAGE_ANNOUNCEMENT",
        "content": {
            "type": "LINK",
            "title": "MCMR: mainboard code graph and enforcement history",
            "description": "1 fact tables and 1 rule jobs MCMR published for mainboard.",
            "link": "/pipelines/urn:li:dataFlow:(mcmr,mainboard,PROD)",
        },
        "created": 0,
        "lastModified": 0,
    }


def test_a_project_states_its_writeback_options_flat_and_reads_them_grouped() -> None:
    """The options a project writes stay flat while the model keeps them where they belong."""
    settings = DataHubSettings.from_mapping(
        {
            "server": "http://localhost:8080",
            "owner": "pedro",
            "domain": "Repositories",
            "announce": True,
            "publish_runs": True,
        }
    )

    assert settings.writeback.owner == "pedro"
    assert settings.writeback.publish_runs is True
    assert settings.timeout_seconds == 120
    assert domain_urn(settings.writeback.domain) == "urn:li:domain:mcmr-repositories"


def test_a_link_is_absolute_about_where_a_reader_browses_this_catalog() -> None:
    """A quickstart answers GMS and its front end on two ports, and anything else on one."""
    quickstart = DataHubSettings(server="http://localhost:8080")
    hosted = DataHubSettings(server="https://acme.example/")
    stated = DataHubSettings.from_mapping(
        {"server": "http://localhost:8080", "frontend": "https://ui.example"}
    )

    assert quickstart.frontend == "http://localhost:9002"
    assert hosted.frontend == "https://acme.example"
    assert stated.frontend == "https://ui.example"
