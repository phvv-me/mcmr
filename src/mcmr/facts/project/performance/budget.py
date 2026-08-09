from pydantic import Field

from .groups import PerformanceBudgetFields


class PerformanceBudget(PerformanceBudgetFields):
    """Retain one critical budget and the artifacts needed to repeat its check."""

    variance_policy: str = Field(
        default="", description="stated tolerance for run to run variance in the measured metric"
    )
    check_command: str = Field(
        default="", description="command that reruns the regression check for this budget"
    )
    owner: str = Field(
        default="", description="team or person accountable for the performance budget"
    )
    last_outcome: str = Field(
        default="", description="most recent recorded result of running the regression check"
    )
