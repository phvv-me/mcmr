from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from .....domain.primitives import NonEmptyStr


class RunbookTriggerFields(FrozenModel):
    """Retain trigger identity, scope, ownership, commands, and verification."""

    name: NonEmptyStr = Field(description="name of the trigger, such as an alert or scenario")
    in_scope: bool = Field(
        default=True, description="whether the trigger counts toward runbook coverage"
    )
    owner: str = Field(
        default="", description="team or person accountable for the runbook, empty when unassigned"
    )
    prerequisites: list[str] = Field(
        default=[], description="conditions or access required before running the procedure"
    )
    commands: list[str] = Field(
        default=[], description="commands the runbook executes to resolve the trigger"
    )
    verification_age_days: NonNegativeInt | None = Field(
        default=None,
        description="days since the runbook was last verified, unset when never verified",
    )
    self_healing: bool = Field(
        default=False,
        description="whether the trigger resolves automatically without a manual runbook",
    )
