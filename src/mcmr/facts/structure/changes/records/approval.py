from patos import FrozenModel
from pydantic import Field

from .....domain.primitives import NonEmptyStr


class ChangeApproval(FrozenModel):
    """Retain one approval without collapsing all approvals into a verdict."""

    reviewer: NonEmptyStr = Field(description="identifier of the person who gave this approval")
    approved: bool = Field(default=True, description="whether this approval was affirmative")
    eligible: bool = Field(
        default=True, description="whether the reviewer counts toward independent review"
    )
