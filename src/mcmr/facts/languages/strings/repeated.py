from typing import Annotated, Literal

from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ...foundation import NodeRef


class RepeatedStringExpression(FrozenModel):
    """Retain one nonempty string literal multiplied by a fixed integer."""

    kind: Literal["fixed-repetition"] = Field(
        default="fixed-repetition",
        description="discriminator identifying this as a fixed repetition expression",
    )
    node: NodeRef = Field(description="syntax node the repetition expression occupies")
    literal: Annotated[str, Field(min_length=1)] = Field(
        description="nonempty string literal being repeated"
    )
    repetition_count: NonNegativeInt = Field(
        default=0, description="fixed integer the literal is multiplied by"
    )
