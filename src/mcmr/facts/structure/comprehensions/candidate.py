from typing import TYPE_CHECKING

from pydantic import Field

from .groups import SetLoopFields

if TYPE_CHECKING:
    from ...foundation import NodeRef


class SetLoopCandidate(SetLoopFields):
    """Retain one set initialization and a convertible following loop."""

    loop: NodeRef | None = Field(default=None, description="syntax node of the whole for loop")
    element: NodeRef | None = Field(
        default=None,
        description="syntax node of the expression added to the set, when the edit is safe",
    )
    target: NodeRef | None = Field(
        default=None, description="syntax node of the loop's target variable"
    )
    iterable: NodeRef | None = Field(
        default=None, description="syntax node of the expression the loop iterates over"
    )
    conditions: list[NodeRef] = Field(
        default=[], description="syntax nodes of the if conditions guarding the set add"
    )
