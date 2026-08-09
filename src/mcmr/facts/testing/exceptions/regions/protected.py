from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ....foundation import NodeRef


class ProtectedRegion(FrozenModel):
    """Retain the protected statement and setup leading into one try region."""

    statement: NodeRef | None = Field(
        default=None, description="syntax node of the try statement itself"
    )
    leading_assignments: list[NodeRef] = Field(
        default=[], description="literal-only setup statements movable ahead of the try block"
    )
    protected_statements: list[NodeRef] = Field(
        default=[], description="syntax nodes of the statements the try block guards"
    )
    leading_literal_assignment_count: NonNegativeInt = Field(
        default=0, description="how many leading assignments the try block carries"
    )
    has_following_raising_operation: bool = Field(
        default=False, description="whether the statement after the leading assignments can raise"
    )
