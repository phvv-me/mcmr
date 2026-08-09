from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .trigger import RunbookTrigger


class RunbookFact(Fact):
    """Describe operational triggers and their linked procedures."""

    triggers: list[RunbookTrigger] = Field(
        default=[], description="operational triggers and their linked runbooks"
    )
