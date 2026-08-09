from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from .....domain.primitives import NonEmptyStr
from ....foundation import NodeRef, SourceSpan


class PublicExport(FrozenModel):
    """Retain one explicit export and use of that public route."""

    name: NonEmptyStr = Field(description="public name this export declares")
    target: NonEmptyStr = Field(description="dotted name the export resolves to")
    consumer_count: NonNegativeInt = Field(
        default=0,
        description="distinct repository files that consume this export through its route",
    )
    nodes: list[NodeRef] = Field(
        default=[], description="syntax nodes where this export is declared, such as in __all__"
    )
    span: SourceSpan = Field(description="source location of this export declaration")
