import asyncio
from abc import ABC, abstractmethod
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING

from pydantic import JsonValue, PositiveInt

from ..queries.runtime import ClassificationBackend
from .batch import BatchProtocol
from .candidate import CandidateProtocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ...domain.contracts import Criterion, ModelProvenance
    from ..queries.contracts import Assessment, Classification, ModelCandidate


class BatchedBackend(ClassificationBackend, ABC):
    """Answer bounded candidate batches through one schema-constrained model turn each."""

    batch_size: PositiveInt = 32

    @cached_property
    def limiter(self) -> asyncio.Semaphore:
        """Share one turn bound across every contextual rule in this backend."""
        return asyncio.Semaphore(self.workers)

    async def assess_candidate(
        self,
        candidate: ModelCandidate,
        *,
        criteria: Sequence[Criterion],
        instructions: str,
    ) -> Assessment:
        """Assess all predicates for one normalized candidate in one model turn."""
        protocol = CandidateProtocol(candidate=candidate, instructions=instructions)
        validated = protocol.criteria(criteria)
        source, provenance = await self.turn(
            protocol.assessment_schema(validated),
            prompt=protocol.assessment_prompt(validated),
            name="assessment",
        )
        return protocol.assessment(source, validated, provenance)

    async def assess_many(
        self,
        candidates: Sequence[ModelCandidate],
        *,
        criteria: Sequence[Criterion],
        instructions: str,
    ) -> Sequence[Assessment]:
        """Assess bounded candidate batches through one model turn per batch."""
        if not candidates:
            return []
        validated = CandidateProtocol(
            candidate=candidates[0],
            instructions=instructions,
        ).criteria(criteria)
        batches = self._batches(candidates, self.batch_size)
        grouped = await asyncio.gather(
            *(self._assessment_batch(batch, validated, instructions) for batch in batches)
        )
        return self._answered(grouped)

    async def classify_candidate[Category: StrEnum](
        self,
        candidate: ModelCandidate,
        *,
        category: type[Category],
        instructions: str,
    ) -> Classification[Category]:
        """Classify one normalized table candidate without reconstructing a fact model."""
        protocol = CandidateProtocol(candidate=candidate, instructions=instructions)
        source, provenance = await self.turn(
            protocol.classification_schema(category),
            prompt=protocol.classification_prompt(category),
            name="classification",
        )
        return protocol.classification(source, category, provenance)

    async def classify_many[Category: StrEnum](
        self,
        candidates: Sequence[ModelCandidate],
        *,
        category: type[Category],
        instructions: str,
    ) -> Sequence[Classification[Category]]:
        """Classify bounded candidate batches through one model turn per batch."""
        if not candidates:
            return []
        batches = self._batches(candidates, self.batch_size)
        grouped = await asyncio.gather(
            *(self._classification_batch(batch, category, instructions) for batch in batches)
        )
        return self._answered(grouped)

    @abstractmethod
    async def turn(
        self,
        schema: Mapping[str, JsonValue],
        *,
        prompt: str,
        name: str,
    ) -> tuple[str, ModelProvenance]:
        """Run one schema-constrained turn and return its answer source and provenance."""
        raise NotImplementedError

    @staticmethod
    def _answered[Outcome](
        groups: Sequence[tuple[Sequence[Outcome], OSError | RuntimeError | ValueError | None]],
    ) -> list[Outcome]:
        """Flatten each batch's outcomes, or raise the shared turn failure once no batch answered.

        A batch whose turn answered but whose content failed to parse stays isolated, because the
        turn itself proved this backend can run and only that one response was unusable. A call
        where not one batch's turn ever answered was never isolating a bad response, it was hiding
        a backend that cannot run, so the failure behind its fallback candidates surfaces here
        instead of a report full of manufactured uncertainty.
        """
        turn_failures = [error for _, error in groups if error is not None]
        if groups and len(turn_failures) == len(groups):
            raise turn_failures[-1]
        return [outcome for outcomes, _ in groups for outcome in outcomes]

    @staticmethod
    def _batches[Item](candidates: Sequence[Item], size: int) -> list[Sequence[Item]]:
        """Partition candidates without copying their retained evidence models."""
        return [candidates[start : start + size] for start in range(0, len(candidates), size)]

    async def _assessment_batch(
        self,
        candidates: Sequence[ModelCandidate],
        criteria: Sequence[Criterion],
        instructions: str,
    ) -> tuple[Sequence[Assessment], OSError | RuntimeError | ValueError | None]:
        """Isolate a failed assessment batch and tag turn failures.

        A response parsing failure remains local to its batch.
        """
        async with self.limiter:
            protocol = BatchProtocol(candidates=list(candidates), instructions=instructions)
            try:
                source, provenance = await self.turn(
                    protocol.assessment_schema(criteria),
                    prompt=protocol.assessment_prompt(criteria),
                    name="assessment",
                )
            except (OSError, RuntimeError, ValueError) as error:
                return [
                    self._failed_assessment(candidate, criteria, error) for candidate in candidates
                ], error
            try:
                return protocol.assessments(source, criteria, provenance), None
            except (OSError, RuntimeError, ValueError) as error:
                return [
                    self._failed_assessment(candidate, criteria, error) for candidate in candidates
                ], None

    async def _classification_batch[Category: StrEnum](
        self,
        candidates: Sequence[ModelCandidate],
        category: type[Category],
        instructions: str,
    ) -> tuple[Sequence[Classification[Category]], OSError | RuntimeError | ValueError | None]:
        """Isolate a failed classification batch and tag turn failures.

        A response parsing failure remains local to its batch.
        """
        async with self.limiter:
            protocol = BatchProtocol(candidates=list(candidates), instructions=instructions)
            try:
                source, provenance = await self.turn(
                    protocol.classification_schema(category),
                    prompt=protocol.classification_prompt(category),
                    name="classification",
                )
            except (OSError, RuntimeError, ValueError) as error:
                return [
                    self._failed_classification(candidate, category, error)
                    for candidate in candidates
                ], error
            try:
                return protocol.classifications(source, category, provenance), None
            except (OSError, RuntimeError, ValueError) as error:
                return [
                    self._failed_classification(candidate, category, error)
                    for candidate in candidates
                ], None
