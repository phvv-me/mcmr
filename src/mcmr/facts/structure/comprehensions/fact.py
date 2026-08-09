from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from .candidate import SetLoopCandidate


class ComprehensionFact(Fact):
    """Describe one comprehension and its nested clauses."""

    loop_counts: list[NonNegativeInt] = Field(
        default=[], description="for and async for clause count of every comprehension found"
    )
    set_loop_candidates: list[SetLoopCandidate] = Field(
        default=[], description="manual set building loops convertible to a set comprehension"
    )
