from enum import StrEnum, auto
from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import Field

from ...foundation import NodeRef

if TYPE_CHECKING:
    from .mapping import MappingEntry


class Expression(FrozenModel):
    """Retain one resolved expression and calls producing its value."""

    class LiteralKind(StrEnum):
        """Name the shape of a literal source expression."""

        NONE = auto()
        STRING = auto()
        NUMBER = auto()
        BOOLEAN = auto()
        MAPPING = auto()
        SEQUENCE = auto()

    text: str = Field(default="", description="verbatim source text of the expression")
    qualified_name: str = Field(
        default="", description="dotted name the expression resolves to, when it is a reference"
    )
    literal_kind: LiteralKind = Field(
        default=LiteralKind.NONE, description="shape of the expression when it is a literal"
    )
    resolved_type: str = Field(
        default="", description="resolved type of the expression, empty when unresolved"
    )
    arguments: list["Expression"] = Field(
        default=[], description="nested expressions this expression is called or built with"
    )
    entries: list["MappingEntry"] = Field(
        default=[], description="key value pairs, when the expression is a literal mapping"
    )
    node: NodeRef | None = Field(
        default=None, description="syntax node the expression occupies, when captured"
    )
