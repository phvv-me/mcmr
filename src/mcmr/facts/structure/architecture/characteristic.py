from typing import TYPE_CHECKING, Literal

from pydantic import Field

from .groups import ArchitectureFields

if TYPE_CHECKING:
    from pydantic import NonNegativeInt


class ArchitectureCharacteristic(ArchitectureFields):
    """Retain raw evidence declared for one architecture quality."""

    owner: str = Field(
        default="", description="team or person accountable for this architecture characteristic"
    )
    scope: str = Field(default="", description="part of the system the check covers")
    observation_age_days: NonNegativeInt | None = Field(
        default=None, description="age in days of the retained result, when one has been recorded"
    )
    verification: Literal["ci", "manual", "repeatable_review", "none"] = Field(
        default="none", description="how the retained result was verified"
    )
