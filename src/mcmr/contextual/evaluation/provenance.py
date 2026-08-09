from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import NonNegativeInt

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Self

    from ...domain.contracts import ModelProvenance


class ProvenanceTotals(FrozenModel):
    """Sum the token counters a collection of model provenances reported."""

    cached_input_tokens: NonNegativeInt = 0
    input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0
    reasoning_tokens: NonNegativeInt = 0

    @classmethod
    def of(cls, provenances: Iterable[ModelProvenance]) -> Self:
        """Total every token counter across the given provenances."""
        turns = list(provenances)
        return cls(
            cached_input_tokens=sum(turn.cached_input_tokens for turn in turns),
            input_tokens=sum(turn.input_tokens for turn in turns),
            output_tokens=sum(turn.output_tokens for turn in turns),
            reasoning_tokens=sum(turn.reasoning_tokens for turn in turns),
        )
