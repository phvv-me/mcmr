from patos import FrozenModel
from pydantic import Field

from ..span import SourceSpan


class NodeRef(FrozenModel):
    """Address one resolved syntax node and retain the exact source it spans.

    A fix names edited nodes through these handles, so a language backend renders the rewrite from
    a typed request instead of accepting a byte range computed inside a rule.
    """

    id: str = Field(description="identifier of the resolved graph node this handle addresses")
    span: SourceSpan = Field(description="source range the node occupies")
    kind: str = Field(
        default="", description="syntax kind label of the node, empty when unresolved"
    )
    text: str = Field(
        default="", description="verbatim source text the node spans, empty when unresolved"
    )
