from patos import FrozenModel
from pydantic import Field

from ...foundation import SourceSpan, SyntaxTraversal


class SyntaxNode(SyntaxTraversal, FrozenModel):
    """Retain one declaration tree node and the source it spans."""

    kind: str = Field(description="language-neutral category this node represents")
    name: str = Field(default="", description="identifier name this node carries, when it has one")
    text: str = Field(
        default="", description="verbatim source text this node spans, when retained"
    )
    span: SourceSpan | None = Field(default=None, description="source range this node occupies")
    children: list["SyntaxNode"] = Field(
        default=[], description="nested syntax nodes directly beneath this one"
    )
