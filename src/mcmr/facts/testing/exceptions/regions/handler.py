from patos import FrozenModel
from pydantic import Field

from ....foundation import NodeRef


class ExceptionHandler(FrozenModel):
    """Retain one caught type and the statements its handler executes."""

    caught: str = Field(
        default="", description="source text of the caught exception type, empty when bare"
    )
    caught_is_tuple: bool = Field(
        default=False, description="whether the caught type is a tuple of multiple exception types"
    )
    alias: str = Field(
        default="", description="name the caught exception is bound to, empty when none"
    )
    body: list[NodeRef] = Field(
        default=[], description="syntax nodes of the statements this handler executes"
    )
