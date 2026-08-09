from typing import TYPE_CHECKING

from pydantic import Field

from .groups import SecurityBoundaryFields

if TYPE_CHECKING:
    from pydantic import NonNegativeInt


class SecurityBoundary(SecurityBoundaryFields):
    """Retain one boundary before contextual threat analysis."""

    residual_risks: list[str] = Field(
        default=[], description="risks accepted rather than mitigated at this boundary"
    )
    owner: str = Field(
        default="",
        description="team or person accountable for the boundary, empty when unassigned",
    )
    review_age_days: NonNegativeInt | None = Field(
        default=None,
        description="days since the threat model was last reviewed, unset when never reviewed",
    )
    inherited_model: str = Field(
        default="",
        description="name of the parent threat model this boundary inherits from, empty when it "
        "has its own",
    )
