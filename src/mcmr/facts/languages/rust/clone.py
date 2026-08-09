from patos import FrozenModel
from pydantic import Field, NonNegativeInt, PositiveInt


class CloneCall(FrozenModel):
    """Retain one copy made where a borrow could not be arranged."""

    receiver: str = Field(
        default="",
        description="expression the clone or to_owned call is invoked on, empty when unresolved",
    )
    owner: str = Field(
        default="", description="function or method the copy occurs in, empty at module level"
    )
    line: PositiveInt = Field(default=1, description="line the copy is made on")
    loop_depth: NonNegativeInt = Field(
        default=0,
        description="number of enclosing for, while, or loop bodies the copy sits inside",
    )
