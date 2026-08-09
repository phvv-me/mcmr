from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .definition import AlertDefinition


class AlertFact(Fact):
    """Describe operational alert definitions without judging actionability."""

    alerts: list[AlertDefinition] = Field(
        default=[], description="declared alert definitions this fact retains"
    )
