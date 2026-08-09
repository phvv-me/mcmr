from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .budget import PerformanceBudget


class PerformanceDecisionFact(Fact):
    """Describe declared performance budgets and repeatable check inputs."""

    budgets: list[PerformanceBudget] = Field(
        default=[], description="performance budgets this fact declares"
    )
