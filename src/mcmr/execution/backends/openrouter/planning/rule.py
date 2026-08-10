from enum import StrEnum
from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import JsonValue, NonNegativeInt

from ....queries import ModelQuery
from ....queries.contracts import ModelMode
from ...batch import BatchProtocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class RepositoryRule(FrozenModel):
    """Keep one rule's candidate slice tied to its original candidate positions."""

    index: NonNegativeInt
    query: ModelQuery[StrEnum]
    rows: list[dict[str, JsonValue]]
    positions: list[NonNegativeInt]
    batch: BatchProtocol

    @property
    def answer_rows(self) -> int:
        """Count candidate rows the model must return for this slice."""
        return len(self.batch.candidates)

    @property
    def answer_units(self) -> int:
        """Count scalar values the model must return for this candidate slice."""
        values = 1 if self.query.mode is ModelMode.CLASSIFY else len(self.query.criteria)
        return len(self.batch.candidates) * values

    @property
    def evidence(self) -> set[str]:
        """Return durable evidence identities this rule slice reads."""
        return {
            identifier for candidate in self.batch.candidates for identifier in candidate.retained
        }

    def combined(self, other: RepositoryRule) -> RepositoryRule:
        """Join disjoint slices of the same rule back into original candidate order."""
        if self.index != other.index:
            raise ValueError("Repository rule slices must share one original rule")
        entries = sorted(
            [
                *zip(self.positions, self.rows, self.batch.candidates, strict=True),
                *zip(other.positions, other.rows, other.batch.candidates, strict=True),
            ],
            key=lambda entry: entry[0],
        )
        return RepositoryRule(
            index=self.index,
            query=self.query,
            rows=[entry[1] for entry in entries],
            positions=[entry[0] for entry in entries],
            batch=BatchProtocol(
                candidates=[entry[2] for entry in entries],
                instructions=self.batch.instructions,
            ),
        )

    def selected(self, selected: Sequence[int]) -> RepositoryRule:
        """Return one ordered candidate subset without rebuilding normalized evidence."""
        return RepositoryRule(
            index=self.index,
            query=self.query,
            rows=[self.rows[position] for position in selected],
            positions=[self.positions[position] for position in selected],
            batch=BatchProtocol(
                candidates=[self.batch.candidates[position] for position in selected],
                instructions=self.batch.instructions,
            ),
        )
