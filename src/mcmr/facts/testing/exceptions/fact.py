from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .regions import ExceptionRegion


class TryBlockFact(Fact):
    """Describe one try statement and its handlers."""

    regions: list[ExceptionRegion] = Field(
        default=[], description="try statements this file declares, with their setup and clauses"
    )
