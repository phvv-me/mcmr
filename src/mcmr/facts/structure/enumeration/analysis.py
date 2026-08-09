from typing import Literal

from patos import FrozenModel
from pydantic import Field

from .member import EnumMember


class EnumAnalysis(FrozenModel):
    """Retain one standard enum declaration and its literal members."""

    name: str = Field(description="name of the declared enum class")
    kind: Literal["enum", "int_enum", "str_enum", "flag", "int_flag"] = Field(
        description="enum base the class derives from"
    )
    members: list[EnumMember] = Field(
        default=[], description="explicit members the enum class declares"
    )
    overrides_generate_next_value: bool = Field(
        default=False, description="whether the enum class defines its own `_generate_next_value_`"
    )
