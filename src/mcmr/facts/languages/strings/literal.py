from typing import Literal

from patos import FrozenModel
from pydantic import Field, PositiveInt

from ...foundation import NodeRef


class LiteralStringExpression(FrozenModel):
    """Retain lexical and runtime properties of one folded string literal."""

    kind: Literal["literal"] = Field(
        default="literal", description="discriminator identifying this as a folded literal"
    )
    node: NodeRef = Field(description="syntax node the literal expression occupies")
    runtime_value: str = Field(description="folded runtime value of the string literal")
    literal_fragment_count: PositiveInt = Field(
        default=1,
        description="number of adjacent string tokens Python implicitly concatenates into this "
        "value",
    )
    wraps_single_runtime_line: bool = Field(
        default=False,
        description="whether the value contains no newline despite being split across fragments",
    )
