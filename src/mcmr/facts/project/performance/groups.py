from patos import FrozenModel
from pydantic import Field, NonNegativeFloat

from ....domain.primitives import NonEmptyStr


class PerformanceBudgetFields(FrozenModel):
    """Retain budget identity, limit, unit, workload, environment, and baseline."""

    name: NonEmptyStr = Field(description="name identifying the performance budget")
    critical: bool = Field(
        default=True, description="whether the budget is a required regression guard"
    )
    limit: NonNegativeFloat | None = Field(
        default=None, description="numeric threshold the measured metric must stay within"
    )
    unit: str = Field(
        default="", description="unit the limit and measured metric are expressed in"
    )
    workload: str = Field(default="", description="workload the budget measures performance under")
    environment: str = Field(
        default="", description="environment the budget's measurement is taken in"
    )
    baseline: str = Field(
        default="", description="reference point the measurement is compared against"
    )
