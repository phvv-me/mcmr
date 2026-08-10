import json

import polars as pl
import pytest
from pydantic import JsonValue, TypeAdapter

from mcmr.execution import Assessment, Classification, ModelCandidate, backends
from mcmr.execution.queries import ModelMode, ModelQuery
from mcmr.facts import Evidence

from ...backend_values import candidate, criteria, provenance
from ...fakes import Category


def query(*, mode: ModelMode = ModelMode.CLASSIFY) -> ModelQuery[Category]:
    """Build one controlled query without coupling protocol tests to a fact table."""
    if mode is ModelMode.CLASSIFY:
        return ModelQuery(
            candidates=pl.LazyFrame(),
            category=Category,
            instructions="Judge retained structure.",
            mode=mode,
        )
    return ModelQuery(
        candidates=pl.LazyFrame(),
        category=Category,
        instructions="Assess retained structure.",
        mode=mode,
        criteria=list(criteria()),
        decision_table=[],
        default=Category.UNCERTAIN,
        uncertain=Category.UNCERTAIN,
    )


def normalized_protocol() -> backends.RepositoryProtocol:
    """Build repeated evidence and three distinct candidate shapes."""
    shared = Evidence(signal="shared", detail='{"kind":"design"}', source="src/a.py")
    compact = ModelCandidate(
        fact_id="compact",
        path="src/a.py",
        subject={"fields": {"kind": "design"}, "records": [], "values": []},
        evidence=[shared],
    )
    extended = ModelCandidate(
        fact_id="extended",
        path="src/b.py",
        subject={
            "fields": {"other": 1},
            "records": ["plain", {"raw": 1}],
            "values": ["v"],
        },
        evidence=[Evidence(signal="plain", detail="not json", source="src/b.py", confidence=0.5)],
    )
    scalar = ModelCandidate(
        fact_id="scalar", path="src/c.py", subject="whole repository", evidence=[shared]
    )
    return backends.RepositoryProtocol(
        batches=[
            backends.BatchProtocol(
                candidates=[compact, extended, scalar], instructions="Judge retained structure."
            )
        ]
    )


def test_repository_protocol_normalizes_repeated_evidence_and_subjects() -> None:
    """The shared prompt stores evidence once and retains irreducible subject data."""
    protocol = normalized_protocol()
    stable, _ = protocol.prompt([query()]).split("\n\nQuestions\n", maxsplit=1)

    assert protocol.evidence.payloads == {
        "e0": {"d": {"kind": "design"}, "s": "src/a.py"},
        "e1": {"d": "not json", "s": "src/b.py", "p": 0.5},
    }
    assert protocol.context["c"] == {
        "c0": {"e": ["e0"]},
        "c1": {
            "e": ["e1"],
            "f": {"other": 1},
            "r": ["plain", {"raw": 1}],
            "v": ["v"],
        },
        "c2": {"e": ["e0"], "s": "whole repository"},
    }
    assert (
        "Shared context" in stable,
        protocol.evidence.candidate_aliases[0],
        protocol.cache_key([query()]).startswith("mcmr-"),
    ) == (True, ["c0", "c1", "c2"], True)


def test_repository_protocol_closes_each_compact_candidate_schema() -> None:
    """One compact question schema aligns values, confidence, and reasons."""
    protocol = normalized_protocol()
    answer_schema = protocol.output_schema([query()])
    properties = TypeAdapter(dict[str, JsonValue]).validate_python(answer_schema["properties"])
    question_schema = TypeAdapter(dict[str, JsonValue]).validate_python(properties["q0"])
    properties = TypeAdapter(dict[str, JsonValue]).validate_python(question_schema["properties"])
    values = TypeAdapter(dict[str, JsonValue]).validate_python(properties["v"])
    details = TypeAdapter(dict[str, JsonValue]).validate_python(properties["d"])
    detail = TypeAdapter(dict[str, JsonValue]).validate_python(details["items"])
    detail_properties = TypeAdapter(dict[str, JsonValue]).validate_python(detail["properties"])

    assert [*properties] == ["v", "p", "d"]
    assert (values["minItems"], values["maxItems"]) == (3, 3)
    assert (details["minItems"], details["maxItems"], detail["type"]) == (0, 3, "object")
    assert [*detail_properties] == ["a", "r"]


def test_repository_protocol_compacts_repeated_text_and_drops_null_fields() -> None:
    """The TRON document keeps known values while compacting text and unknowns."""
    repeated = "long source body " * 20
    candidates = [
        ModelCandidate(
            fact_id=f"fact-{index}",
            path="src/a.py",
            subject={"fields": {"source": repeated, "unknown": None}},
            evidence=[
                Evidence(
                    signal=f"fact-{index}",
                    detail=json.dumps({"source": repeated, "unknown": None}),
                    source="src/a.py",
                )
            ],
        )
        for index in range(2)
    ]
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=candidates, instructions="Judge structure.")]
    )

    assert protocol.evidence.payloads == {
        "e0": {"d": {"source": repeated}, "s": "src/a.py"},
        "e1": {"d": {"source": repeated}, "s": "src/a.py"},
    }
    assert protocol.context["c"] == {"c0": {"e": ["e0"]}, "c1": {"e": ["e1"]}}
    stable, _ = protocol.prompt([query()]).split("\n\nQuestions\n", maxsplit=1)
    assert ": d,s" in stable
    assert "\nText blocks\n@0\n" in stable
    assert stable.count(repeated) == 1


def test_repository_protocol_rejects_missing_candidate_answers() -> None:
    """Compact answers cannot change candidate cardinality."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )

    with pytest.raises(ValueError, match="different candidate judgment identities"):
        protocol.outcomes(
            json.dumps({"q0": {"v": [], "p": [], "d": []}}),
            [query()],
            provenance(),
        )


def test_repository_protocol_attaches_the_candidate_evidence_by_construction() -> None:
    """A keyed judgment inherits all evidence retained for its exact candidate."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )

    outcomes = protocol.outcomes(
        json.dumps(
            {
                "q0": {
                    "v": [["supported"]],
                    "p": [0.9],
                    "d": [],
                }
            }
        ),
        [query()],
        provenance(),
    )

    outcome = outcomes[0][0]
    assert isinstance(outcome, Classification)
    assert outcome.evidence == [*candidate().retained]


def test_repository_protocol_rejects_different_candidate_identity() -> None:
    """A right-sized answer cannot substitute another question identity."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )
    with pytest.raises(ValueError, match="different candidate judgment identities"):
        protocol.outcomes(
            json.dumps(
                {
                    "q0": {
                        "v": [["supported"]],
                        "p": [0.9],
                        "d": [{"a": "a9", "r": "The answer identity was substituted."}],
                    }
                }
            ),
            [query()],
            provenance(),
        )


def test_repository_protocol_rejects_a_wrong_rubric_value_count() -> None:
    """One candidate cannot omit an assessment value from its ordered vector."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )

    with pytest.raises(ValueError, match="different number of rubric values"):
        protocol.outcomes(
            json.dumps(
                {
                    "q0": {
                        "v": [["yes"]],
                        "p": [0.9],
                        "d": [],
                    }
                }
            ),
            [query(mode=ModelMode.ASSESS)],
            provenance(),
        )


def test_repository_protocol_supplies_a_reason_for_a_failed_assessment() -> None:
    """A missing failed-predicate detail receives one deterministic local explanation."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )

    outcome = protocol.outcomes(
        json.dumps({"q0": {"v": [["yes", "no"]], "p": [0.8], "d": []}}),
        [query(mode=ModelMode.ASSESS)],
        provenance(),
    )[0][0]

    assert isinstance(outcome, Assessment)
    assert all(
        answer.reasoning
        == "Retained evidence supports this assessment. structure contradicted is no."
        for answer in outcome.answers
    )


def test_repository_protocol_supplies_a_reason_for_an_unjudged_category() -> None:
    """A required missing detail receives a deterministic local explanation."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )
    judged = query().judged(
        {
            "supported": "reports nothing and records the subject as acceptable",
            "uncertain": "reports nothing and leaves the subject unjudged",
        }
    )

    outcome = protocol.outcomes(
        json.dumps(
            {
                "q0": {
                    "v": [["uncertain"]],
                    "p": [0.5],
                    "d": [],
                }
            }
        ),
        [judged],
        provenance(),
    )[0][0]

    assert isinstance(outcome, Classification)
    assert outcome.reasoning.startswith("Retained evidence supports uncertain.")


def test_repository_protocol_retains_each_classification_effect() -> None:
    """The compact rubric states what every selected category makes MCMR report."""
    protocol = backends.RepositoryProtocol(
        batches=[backends.BatchProtocol(candidates=[candidate()], instructions="Judge structure.")]
    )
    judged = query().judged(
        {
            "supported": "reports nothing and records the subject as acceptable",
            "uncertain": "reports nothing and leaves the subject unjudged",
        }
    )

    prompt = protocol.prompt([judged])

    assert "detail omitted | reports nothing and records the subject as acceptable" in prompt
    assert "detail required | reports nothing and leaves the subject unjudged" in prompt
