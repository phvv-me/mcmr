from typing import TYPE_CHECKING

from mcmr.plugins import RuleJob, RuleTables
from mcmr_datahub.services.publication import (
    category_urn,
    dataset_urn,
    defined,
    described,
    scope_urn,
    word_urn,
)

from ..support import aspect, emitted, run_graph, table, timeline

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import JsonValue

_TABLE = table()

_LABELLED = run_graph("structure")


def terms(entity: Mapping[str, JsonValue]) -> list[str]:
    """Return the glossary terms one captured entity was published with."""
    held = aspect(entity, "glossaryTerms")["terms"]
    assert isinstance(held, list)
    return [str(item["urn"]) for item in held if isinstance(item, dict)]


def test_a_rule_carries_the_lane_it_answers_in_and_the_family_it_belongs_to() -> None:
    """A rulebook of hundreds is only readable if a reader can filter it down to one lane."""
    entities, _ = emitted("summarize", [timeline("ALL-DUPL0005")], graph=_LABELLED)
    rule = entities["datajob"][1]

    assert aspect(rule, "subTypes")["typeNames"] == ["Deterministic rule"]
    assert aspect(rule, "globalTags")["tags"] == [
        {"tag": "urn:li:tag:mcmr-deterministic"},
        {"tag": scope_urn("all")},
    ]
    assert terms(rule) == [
        "urn:li:glossaryTerm:mcmr-family-duplication",
        word_urn("deterministic rule"),
        word_urn("finding"),
        word_urn("repair"),
    ]


def test_a_rule_needing_both_a_model_and_a_network_keeps_both_lanes() -> None:
    """The single type label can only say one thing, so the tags say the rest."""
    estimated = RuleJob(
        rule="PY-ARCH1005",
        tables=RuleTables(primary=_TABLE),
        lanes=["contextual", "external"],
        family="architecture",
    )
    graph = _LABELLED.model_copy(update={"jobs": [estimated]})

    entities, _ = emitted("summarize", graph=graph)
    rule = entities["datajob"][1]

    assert aspect(rule, "subTypes")["typeNames"] == ["Contextual rule"]
    assert aspect(rule, "globalTags")["tags"] == [
        {"tag": "urn:li:tag:mcmr-contextual"},
        {"tag": "urn:li:tag:mcmr-external"},
        {"tag": scope_urn("py")},
    ]
    assert terms(rule)[1:3] == [word_urn("contextual rule"), word_urn("external rule")]
    assert estimated.lane == "contextual"


def test_only_the_lanes_families_scopes_and_groups_a_run_reached_are_published() -> None:
    """An unused tag is clutter, so the vocabulary a run writes is the one it needs."""
    entities, _ = emitted("publish", graph=_LABELLED)

    assert [item["urn"] for item in entities["tag"]] == [
        "urn:li:tag:mcmr-deterministic",
        scope_urn("all"),
        category_urn("structure"),
    ]
    assert [item["urn"] for item in entities["glossaryterm"]][:2] == [
        "urn:li:glossaryTerm:mcmr-family-duplication",
        word_urn("fact table"),
    ]
    assert [item["urn"] for item in entities["glossarynode"]] == [
        "urn:li:glossaryNode:mcmr-rule-families",
        "urn:li:glossaryNode:mcmr-vocabulary",
    ]
    assert aspect(entities["glossaryterm"][0], "glossaryTermInfo")["parentNode"] == (
        "urn:li:glossaryNode:mcmr-rule-families"
    )


def test_every_published_tag_carries_a_colour_and_a_sentence() -> None:
    """A filter list nobody can read at a glance is a list nobody filters by."""
    entities, _ = emitted("publish", graph=_LABELLED)

    stated = [aspect(item, "tagProperties") for item in entities["tag"]]
    assert all(item["colorHex"] and item["description"] and item["name"] for item in stated)
    assert stated[2]["name"] == "facts structure"
    assert stated[1]["name"] == "scope all"


def test_a_fact_table_is_labelled_by_the_group_its_facts_are_defined_in() -> None:
    """The taxonomy on screen is the directory the fact models already live in."""
    entities, _ = emitted("publish", graph=_LABELLED)
    dataset = entities["dataset"][0]

    assert aspect(dataset, "globalTags")["tags"] == [{"tag": category_urn("structure")}]
    assert terms(dataset) == [word_urn("fact table"), word_urn("verdict")]
    assert aspect(dataset, "datasetProperties")["customProperties"] == {
        "family": "LiteralGroupFact",
        "category": "structure",
    }


def test_a_fact_table_from_a_group_nobody_defined_carries_no_group_tag() -> None:
    """A tag is only worth writing when it names something, so an unknown group writes none."""
    entities, _ = emitted("publish", graph=run_graph())

    assert "globalTags" not in entities["dataset"][0]
    assert [item["urn"] for item in entities["tag"]] == [
        "urn:li:tag:mcmr-deterministic",
        scope_urn("all"),
    ]


def test_the_two_flows_say_which_of_them_holds_the_rules_and_which_holds_the_runs() -> None:
    """A reader landing on a flow has to be told what kind of flow they landed on."""
    entities, _ = emitted("publish", graph=_LABELLED)
    repository, rulebook = entities["dataflow"]

    assert terms(repository) == [word_urn("writeback"), word_urn("run")]
    assert terms(rulebook) == [word_urn("rulebook")]


def test_every_core_word_is_published_with_a_definition_under_one_node() -> None:
    """A vocabulary is only shared once both sides can read the same definition of it."""
    entities, _ = emitted("publish", graph=_LABELLED)
    words = [item for item in entities["glossaryterm"] if str(item["urn"]).count("word-")]

    stated = [aspect(item, "glossaryTermInfo") for item in words]
    assert len(stated) == 11
    assert all(item["definition"] and item["termSource"] == "INTERNAL" for item in stated)
    assert {item["parentNode"] for item in stated} == {"urn:li:glossaryNode:mcmr-vocabulary"}
    assert word_urn("intermittent finding") in {str(item["urn"]) for item in words}


def test_a_rule_with_no_lane_keeps_the_plain_type_label() -> None:
    """A graph stating no lane still publishes a rule rather than nothing."""
    graph = _LABELLED.model_copy(
        update={"jobs": [RuleJob(rule="ALL-DUPL0005", tables=RuleTables(primary=_TABLE))]}
    )

    entities, _ = emitted("summarize", graph=graph)
    rule = entities["datajob"][1]

    assert aspect(rule, "subTypes")["typeNames"] == ["Rule"]
    assert aspect(rule, "globalTags")["tags"] == [{"tag": scope_urn("all")}]
    assert terms(rule) == [word_urn("finding"), word_urn("repair")]


def test_a_word_this_vocabulary_never_defined_attaches_nothing() -> None:
    """A term nobody can open is worse than no term, so an unknown word writes none at all."""
    assert defined("invented") == {}
    assert described([]) == {}


def test_a_rule_whose_identifier_names_no_known_language_carries_no_scope_tag() -> None:
    """A tag is written from what a rule identifier proves, never from a guess about it."""
    graph = _LABELLED.model_copy(
        update={"jobs": [RuleJob(rule="ZZZ-DUPL0005", tables=RuleTables(primary=_TABLE))]}
    )

    entities, _ = emitted("summarize", graph=graph)

    assert "globalTags" not in entities["datajob"][1]
    assert dataset_urn(_TABLE).endswith(f"{_TABLE},PROD)")
