from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class ConstantPlacement(FrozenModel):
    """Retain one module constant and statements before its valid anchor."""

    name: str = Field(description="name of the public module constant")
    intervening_statement_count: NonNegativeInt = Field(
        default=0,
        description="unrelated statements between the constant's valid anchor and its declaration",
    )
