from patos import FrozenModel
from pydantic import Field

from ....foundation import NodeRef, SourceSpan


class DataFieldRepair(FrozenModel):
    """Retain the literal a field reference named and the rewrite a catalog proof licenses."""

    node: NodeRef = Field(
        default=NodeRef(id="", span=SourceSpan(path="")),
        description="syntax node of the literal that named the field",
    )
    replacement: str = Field(
        default="",
        description="rewritten literal naming the field's proven successor, empty when unlicensed",
    )
