from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ....domain.primitives import NonEmptyStr


class FeatureFlag(FrozenModel):
    """Retain one flag's dates, role, ownership, states, and cleanup plan."""

    name: NonEmptyStr = Field(description="name of the feature flag")
    age_days: NonNegativeInt = Field(description="days since the feature flag was created")
    role: str = Field(
        default="", description="declared role of the flag, such as a permanent label"
    )
    owner: str = Field(default="", description="team or person responsible for the flag")
    tested_states: list[str] = Field(
        default=[], description="flag states the codebase exercises in tests"
    )
    decision_due_days: int | None = Field(
        default=None,
        description="days until the flag's decision is due, zero or negative when overdue",
    )
    cleanup_plan: str = Field(
        default="", description="plan describing how and when the flag will be removed"
    )
