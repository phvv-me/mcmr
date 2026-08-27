from typing import TYPE_CHECKING

from mcmr.plugins import ModelSpend, RuleJob, RuleTables, RunGraph
from mcmr_datahub import DataHubDirectory, DataHubPeople, DataHubPerson, DataHubSettings

from ..support import aspect, emitted, settings

if TYPE_CHECKING:
    from pydantic import JsonValue

_CAST: dict[str, JsonValue] = {
    "human": {
        "id": "pedro",
        "name": "Pedro Valois",
        "email": "contact@phvv.me",
        "title": "Author of MCMR",
    },
    "agent": {"id": "claude-fable-5", "name": "Claude Fable 5", "title": "Operating agent"},
}

_JUDGED = RuleJob(
    rule="ALL-ARCH1005",
    tables=RuleTables(primary="mainboard/facts/literal_group_fact"),
    lanes=["contextual"],
    family="architecture",
    spend={
        "": ModelSpend(backend="claude", model="claude-sonnet-5", input_tokens=10, output_tokens=1)
    },
)


def owners(entity: dict[str, JsonValue]) -> list[tuple[str, str]]:
    """Return the owner and role pairs one captured entity was published with."""
    held = aspect(entity, "ownership")["owners"]
    assert isinstance(held, list)
    return [(str(item["owner"]), str(item["type"])) for item in held if isinstance(item, dict)]


def directory(graph: RunGraph, **stated: JsonValue) -> DataHubDirectory:
    """Return one directory reading the cast a project stated for this run."""
    configured = settings(**stated)
    return DataHubDirectory(
        configured.writeback.people,
        configured.writeback.owner,
        graph.spent,
    )


def test_a_project_names_its_people_and_the_catalog_shows_them_as_users() -> None:
    """An owner who is only a username is a string, so the run publishes the person behind it."""
    entities, _ = emitted("publish", people=_CAST)
    human, agent = entities["corpuser"]

    assert human["urn"] == "urn:li:corpuser:pedro"
    assert aspect(human, "corpUserInfo") == {
        "active": True,
        "displayName": "Pedro Valois",
        "title": "Author of MCMR",
        "email": "contact@phvv.me",
    }
    assert agent["urn"] == "urn:li:corpuser:claude-fable-5"
    assert aspect(agent, "corpUserInfo")["displayName"] == "Claude Fable 5"
    assert "email" not in aspect(agent, "corpUserInfo")


def test_the_human_answers_for_the_codebase_and_the_agent_operates_it() -> None:
    """Two different responsibilities are two different owners rather than one shared account."""
    entities, _ = emitted("publish", people=_CAST)
    dataset, flow = entities["dataset"][0], entities["dataflow"][0]

    assert owners(flow) == [
        ("urn:li:corpuser:pedro", "BUSINESS_OWNER"),
        ("urn:li:corpuser:claude-fable-5", "TECHNICAL_OWNER"),
    ]
    assert owners(dataset) == [
        ("urn:li:corpuser:pedro", "BUSINESS_OWNER"),
        ("urn:li:corpuser:datahub", "TECHNICAL_OWNER"),
    ]
    assert owners(entities["domain"][1])[0] == ("urn:li:corpuser:pedro", "BUSINESS_OWNER")
    assert owners(entities["dataflow"][1]) == [("urn:li:corpuser:datahub", "TECHNICAL_OWNER")]


def test_a_project_that_names_nobody_still_publishes_under_the_configured_owner() -> None:
    """Inventing a person would be worse than leaving the credit where it already was."""
    entities, _ = emitted("publish")

    assert "corpuser" not in entities
    assert owners(entities["dataflow"][0]) == [("urn:li:corpuser:datahub", "TECHNICAL_OWNER")]


def test_the_model_that_judged_a_rule_is_credited_as_its_steward() -> None:
    """The judge is whichever backend the run actually asked, so nobody configures its name."""
    graph = RunGraph(repository="mainboard", jobs=[_JUDGED])
    stated = directory(graph, people=_CAST)

    assert stated.judge.id == "claude-sonnet-5"
    assert stated.judge.title == "Contextual judge MCMR reaches through the claude backend"
    assert owners(stated.stewardship(_JUDGED, {})) == [
        ("urn:li:corpuser:claude-sonnet-5", "DATA_STEWARD")
    ]


def test_a_rule_keeps_the_judge_another_codebase_already_credited() -> None:
    """A rule is one entity, so a second codebase adds its judge rather than replacing one."""
    graph = RunGraph(repository="mainboard", jobs=[_JUDGED])
    held: dict[str, JsonValue] = {
        "owners": [{"owner": "urn:li:corpuser:gpt", "type": "DATA_STEWARD"}, "broken", {}]
    }

    stated = directory(graph, people=_CAST).stewardship(_JUDGED, held)

    assert owners(stated) == [
        ("urn:li:corpuser:gpt", "DATA_STEWARD"),
        ("urn:li:corpuser:claude-sonnet-5", "DATA_STEWARD"),
    ]


def test_a_rule_no_model_judged_and_no_codebase_owned_states_no_ownership() -> None:
    """A deterministic rule has no judge to credit, so the aspect is simply never written."""
    plain = RuleJob(rule="ALL-DUPL0005", lanes=["deterministic"])
    graph = RunGraph(repository="mainboard", jobs=[plain])

    assert directory(graph).stewardship(plain, {}) == {}
    assert directory(graph, people=_CAST).stewardship(plain, {"owners": "broken"}) == {}


def test_a_person_falls_back_to_their_identity_when_a_project_states_no_name() -> None:
    """A display name nobody wrote is the identity itself rather than an empty row."""
    stated = DataHubPerson(id="pedro")

    assert (stated.named, stated.display) == (True, "pedro")
    assert DataHubPerson().named is False
    assert DataHubPeople.judge(backend="", model="").named is False
    assert DataHubPeople.judge(backend="", model="gpt-5").title == (
        "Contextual judge MCMR reaches through a configured backend"
    )


def test_a_project_states_its_cast_in_configuration_and_never_in_the_package() -> None:
    """The people belong to the repository being published, so settings are where they live."""
    stated = DataHubSettings.from_mapping({"server": "https://catalog.example", "people": _CAST})

    assert stated.writeback.people.human.email == "contact@phvv.me"
    assert stated.writeback.people.agent.title == "Operating agent"
