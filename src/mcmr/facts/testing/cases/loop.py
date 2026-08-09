from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class LiteralTestLoop(FrozenModel):
    """Retain one test-owned loop over literal cases."""

    case_count: NonNegativeInt = Field(description="literal cases the loop iterates over")
    owns_assertion: bool = Field(
        description="whether the loop body contains its own assert statement"
    )
