from patos import FrozenModel
from pydantic import Field

from .....domain.primitives import NonEmptyStr
from .approval import ChangeApproval


class ChangeRecordFields(FrozenModel):
    """Retain change identity, review policy, and approval evidence."""

    identifier: NonEmptyStr = Field(
        description="unique identifier of the change, e.g. a pull request number"
    )
    author: NonEmptyStr = Field(description="identifier of the person who authored the change")
    review_required: bool = Field(
        default=True, description="whether the change's merge path requires review"
    )
    approvals: list[ChangeApproval] = Field(
        default=[], description="approvals recorded against the change"
    )
    emergency: bool = Field(
        default=False, description="whether the change followed an emergency merge path"
    )
    retrospective_review: str = Field(
        default="",
        description="documented retrospective review path for an emergency change, empty "
        "when none",
    )
    mechanical: bool = Field(
        default=False, description="whether the change was produced by an automated bot"
    )
