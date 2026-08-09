from patos import FrozenModel
from pydantic import Field

from ....foundation import NodeRef
from .arm import ConditionalArm


class ConditionalChain(FrozenModel):
    """Retain one ordered chain of conditions and their effects."""

    subject: str = Field(
        default="", description="qualified name of the expression every arm compares against"
    )
    arms: list[ConditionalArm] = Field(
        default=[], description="ordered conditional arms this chain tests"
    )
    has_fallback: bool = Field(
        default=False, description="whether the chain ends in an else clause"
    )
    node: NodeRef = Field(description="syntax node the if statement occupies")
