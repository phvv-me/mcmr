from pydantic import Field

from .groups import ServiceObjectiveFields


class ServiceObjective(ServiceObjectiveFields):
    """Retain one service and the fields required to operate its objective."""

    windows: list[str] = Field(
        default=[], description="measurement windows the objective is evaluated over"
    )
    error_budget_policy: str = Field(
        default="",
        description="action taken when the error budget is exhausted, empty when undeclared",
    )
