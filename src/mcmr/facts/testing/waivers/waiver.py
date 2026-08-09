from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class Waiver(FrozenModel):
    """Retain one suppression and its exact lifecycle metadata."""

    location: str = Field(description="path and line of the suppression comment")
    age_days: NonNegativeInt | None = Field(
        default=None, description="days since the waiver's since date, unknown when unset"
    )
    expires_in_days: int | None = Field(
        default=None, description="days until the waiver's expires date, negative once passed"
    )
    is_overly_broad: bool = Field(
        default=False,
        description="whether the marker suppresses everything on its line rather than one code",
    )
    metadata: dict[str, str] = Field(
        default={}, description="field=value pairs parsed from the suppression comment"
    )
