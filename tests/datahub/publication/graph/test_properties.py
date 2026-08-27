from typing import TYPE_CHECKING

from mcmr.plugins import RuleJob, RuleTables, RunGraph
from mcmr_datahub.services.publication import definitions, property_urn, valued

from ..support import aspect, emitted, run_graph, timeline

if TYPE_CHECKING:
    from pydantic import JsonValue

_LABELLED = run_graph("structure")


def held(entity: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Return the typed properties one captured entity was published with, by short name."""
    stated = aspect(entity, "structuredProperties")["properties"]
    assert isinstance(stated, list)
    return {
        str(item["propertyUrn"]).removeprefix("urn:li:structuredProperty:mcmr."): item["values"]
        for item in stated
        if isinstance(item, dict)
    }


def test_every_typed_property_is_declared_once_under_the_mcmr_namespace() -> None:
    """A definition is written before anything states a value, so a first run creates them all."""
    entities, _ = emitted("publish", graph=_LABELLED)
    declared = {
        str(item["urn"]): aspect(item, "propertyDefinition")
        for item in entities["structuredproperty"]
    }

    assert set(declared) == {
        property_urn(name)
        for name in ("lane", "ruleFamily", "codebase", "findings", "tokensSpent", "flapScore")
    }
    assert declared[property_urn("flapScore")]["valueType"] == "urn:li:dataType:datahub.number"
    assert declared[property_urn("flapScore")]["entityTypes"] == [
        "urn:li:entityType:datahub.dataset"
    ]
    assert declared[property_urn("lane")]["allowedValues"] == [
        {
            "value": {"string": "deterministic"},
            "description": "Computed from repository structure alone.",
        },
        {
            "value": {"string": "contextual"},
            "description": "Judged by a classification backend the caller configured.",
        },
        {
            "value": {"string": "external"},
            "description": "Read from a system outside the repository.",
        },
    ]
    assert "allowedValues" not in declared[property_urn("codebase")]


def test_a_fact_table_and_a_flow_state_the_codebase_that_published_them() -> None:
    """A typed facet is what lets a reader ask the catalog for one codebase everywhere."""
    entities, _ = emitted("publish", graph=_LABELLED)

    assert held(entities["dataset"][0]) == {"codebase": [{"string": "mainboard"}]}
    assert held(entities["dataflow"][0]) == {"codebase": [{"string": "mainboard"}]}


def test_a_rule_states_its_lane_family_findings_and_cost_as_typed_values() -> None:
    """Sorting a rulebook by cost or filtering it by lane is what typed values are for."""
    billed = {"inputTokens": "900", "outputTokens": "100"}
    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005", billed=billed)], graph=_LABELLED)

    assert held(entities["datajob"][1]) == {
        "lane": [{"string": "deterministic"}],
        "ruleFamily": [{"string": "duplication"}],
        "findings": [{"double": 2.0}],
        "tokensSpent": [{"double": 2000.0}],
    }
    assert held(entities["datajob"][0]) == {"codebase": [{"string": "mainboard"}]}


def test_a_value_outside_what_a_property_accepts_is_never_stated() -> None:
    """DataHub rejects a whole entity over one bad value, so a run states only what it proves."""
    invented = RuleJob(
        rule="ALL-DUPL0005",
        tables=RuleTables(primary="mainboard/facts/x"),
        lanes=["invented"],
    )
    graph = _LABELLED.model_copy(update={"jobs": [invented]})

    entities, _ = emitted("summarize", graph=graph)

    assert "lane" not in held(entities["datajob"][1])
    assert valued({"flapScore": "many", "unknown": "1", "codebase": ""}) == {}
    assert definitions()[0]["urn"] == property_urn("lane")


def test_a_rule_nobody_paid_for_and_nothing_reported_states_no_numbers() -> None:
    """A number nobody measured is worse than a blank, so it is simply left out."""
    graph = RunGraph(repository="mainboard", datasets=_LABELLED.datasets, jobs=[_LABELLED.jobs[0]])

    entities, _ = emitted("summarize", graph=graph)
    stated = held(entities["datajob"][1])

    assert stated["findings"] == [{"double": 0.0}]
    assert "tokensSpent" not in stated
