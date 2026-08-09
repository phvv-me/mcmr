from enum import StrEnum
from typing import TYPE_CHECKING

import polars as pl
import pytest

from mcmr.contextual.evaluation import ContextualSweep
from mcmr.domain.contracts import ModelProvenance
from mcmr.execution import (
    Assessment,
    Classification,
    ClassificationBackend,
    CriterionAnswer,
    CriterionValue,
    ModelCandidate,
)
from mcmr.execution.queries import ModelMode, ModelQuery
from mcmr.plugins import Fact

from ..backend_values import criteria

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mcmr.domain.contracts import Criterion

_FIRST = "contextual/ALL-DEMO2001.json"
_SECOND = "contextual/other.json"

_TURN = ModelProvenance(
    backend="claude",
    model="claude-sonnet-5",
    reasoning_effort="high",
    input_tokens=200,
    cached_input_tokens=1500,
    output_tokens=20,
)


class BilledBackend(ClassificationBackend):
    """Answer every candidate with one billed turn, whichever operation the rule planned.

    A real batched harness stamps the same turn on every criterion of one candidate, which is
    what this reproduces, so a test can prove that turn is billed once rather than once each.
    """

    async def assess_candidate(
        self,
        candidate: ModelCandidate,
        *,
        criteria: Sequence[Criterion],
        instructions: str,
    ) -> Assessment:
        return Assessment(
            answers=[
                CriterionAnswer(
                    criterion=criterion.name,
                    value=CriterionValue.YES,
                    reasoning=instructions,
                    evidence=list(candidate.retained),
                    confidence=1.0,
                    provenance=_TURN,
                )
                for criterion in criteria
            ]
        )

    async def classify_candidate[Category: StrEnum](
        self,
        candidate: ModelCandidate,
        *,
        category: type[Category],
        instructions: str,
    ) -> Classification[Category]:
        return Classification(
            value=next(iter(category)),
            reasoning=instructions,
            evidence=list(candidate.retained),
            confidence=1.0,
            provenance=_TURN,
        )


def paired() -> ModelQuery[CriterionValue]:
    """Return one classification over two candidates the run read from two different files."""
    single = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=CriterionValue,
        instructions="Classify support.",
    )
    rows = single.candidates.collect()
    elsewhere = rows.with_columns(
        pl.lit("sweep:other").alias("fact_id"),
        pl.lit(_SECOND).alias("path"),
    )
    return single.model_copy(update={"candidates": pl.concat([rows, elsewhere]).lazy()})


@pytest.mark.anyio
async def test_every_file_a_contextual_rule_read_is_billed_on_its_own() -> None:
    """A verdict about one file was reached by the turns that read it, so the cost lands there."""
    answered = await BilledBackend().answered(paired())

    assert set(answered.spend) == {_FIRST, _SECOND}
    assert answered.spend[_SECOND].properties == {
        "backend": "claude",
        "model": "claude-sonnet-5",
        "reasoningEffort": "high",
        "inputTokens": "200",
        "cachedInputTokens": "1500",
        "outputTokens": "20",
    }
    assert answered.query.findings is not None


@pytest.mark.anyio
async def test_one_assessment_turn_is_billed_once_and_not_once_per_criterion() -> None:
    """Every criterion of a batched candidate carries the same turn, and it was paid for once."""
    assessed = ModelQuery[CriterionValue](
        candidates=paired().candidates,
        category=CriterionValue,
        instructions="Assess support.",
        mode=ModelMode.ASSESS,
        criteria=list(criteria()),
        decision_table=[],
        default=CriterionValue.NO,
        uncertain=CriterionValue.UNKNOWN,
    )
    backend = BilledBackend()

    answered = await backend.answered(assessed)
    stated = await backend.assess_candidate(
        ModelCandidate.from_row(assessed.candidates.collect().to_dicts()[0]),
        criteria=criteria(),
        instructions="Assess support.",
    )

    assert answered.spend[_FIRST].tokens == 1720
    assert len(stated.answers) > 1
    assert backend.spend([{"path": _FIRST}], [stated])[_FIRST].tokens == 1720


@pytest.mark.anyio
async def test_the_plain_resolution_still_returns_only_the_relational_answers() -> None:
    """The spend travels beside the answers, so a caller that wants neither keeps its contract."""
    resolved = await BilledBackend().resolve(paired())

    assert resolved.values.collect().height == 2
