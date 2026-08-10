from typing import TYPE_CHECKING

from patos import FrozenModel

from ...repository import RepositoryProtocol
from .rule import RepositoryRule

if TYPE_CHECKING:
    from collections.abc import Iterable
    from enum import StrEnum

    from ....queries import ModelQuery


class RepositoryPack(FrozenModel):
    """Carry one independently executable collection of normalized rule slices."""

    rules: list[RepositoryRule]

    @property
    def answer_rows(self) -> int:
        """Count every columnar candidate row this pack requests."""
        return sum(rule.answer_rows for rule in self.rules)

    @property
    def answer_units(self) -> int:
        """Count every scalar judgment this pack requests."""
        return sum(rule.answer_units for rule in self.rules)

    @property
    def protocol(self) -> RepositoryProtocol:
        """Build the shared evidence protocol for this exact pack."""
        return RepositoryProtocol(batches=[rule.batch for rule in self.rules])

    @property
    def queries(self) -> list[ModelQuery[StrEnum]]:
        """Return rule contracts in prompt order."""
        return [rule.query for rule in self.rules]

    @classmethod
    def of(cls, rules: Iterable[RepositoryRule]) -> RepositoryPack:
        """Coalesce slices of the same rule while retaining first-seen rule order."""
        grouped: dict[int, RepositoryRule] = {}
        order: list[int] = []
        for rule in rules:
            if rule.index not in grouped:
                grouped[rule.index] = rule
                order.append(rule.index)
            else:
                grouped[rule.index] = grouped[rule.index].combined(rule)
        return cls(rules=[grouped[index] for index in order])
