from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .risk import OperationalRisk


class OperationalRiskFact(Fact):
    """Describe operational risks and the raw signals intended to answer them."""

    risks: list[OperationalRisk] = Field(
        default=[], description="operational risks this fact declares"
    )
