from patos import FrozenModel
from pydantic import Field

from .node import NodeRef


class SymbolRef(FrozenModel):
    """Address one resolved declaration together with every reference bound to it."""

    id: str = Field(description="identifier of the resolved declaration this handle addresses")
    name: str = Field(description="declared name the symbol binds")
    declaration: NodeRef = Field(description="node where the symbol is declared")
    references: list[NodeRef] = Field(
        default=[], description="nodes where the symbol is referenced"
    )
    are_references_complete: bool = Field(
        default=False,
        description="whether every reference to the symbol was resolved and collected",
    )
