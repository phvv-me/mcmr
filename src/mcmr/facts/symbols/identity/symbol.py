from typing import Literal

from patos import FrozenModel
from pydantic import Field

from ...foundation import SymbolRef


class Symbol(FrozenModel):
    """Retain one declaration and its proven value contract."""

    name: str = Field(description="name this symbol binds")
    scope: Literal["module", "class", "local"] = Field(description="scope this name is bound in")
    is_constant_assignment: bool = Field(
        default=False, description="whether the bound name is written in all uppercase"
    )
    returns_boolean: bool = Field(
        default=False,
        description="whether the symbol is a module function annotated to return bool",
    )
    reference: SymbolRef | None = Field(
        default=None,
        description="resolved binding and its references, populated for names bound at module",
    )
