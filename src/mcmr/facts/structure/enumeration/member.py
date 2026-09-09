from patos import FrozenModel
from pydantic import Field

from ...foundation import NodeRef


class EnumMember(FrozenModel):
    """Retain one explicit value and standard auto result at that position."""

    name: str = Field(description="declared name of the enum member")
    explicit_value: str | int = Field(description="literal value the source assigns to the member")
    standard_auto_value: str | int | None = Field(
        description="standard `auto()` value at this position, or None when it is not proven"
    )
    value_node: NodeRef | None = Field(
        default=None, description="syntax node the member's value expression occupies"
    )
