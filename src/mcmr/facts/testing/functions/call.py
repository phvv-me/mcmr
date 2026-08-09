from patos import FrozenModel
from pydantic import Field

from ...foundation import NodeRef


class TestCallSite(FrozenModel):
    """Retain one resolved call a collected test owns."""

    qualified_name: str = Field(description="dotted name the call resolves to")
    path: str = Field(description="repository relative path where the call site occurs")
    node: NodeRef | None = Field(
        default=None, description="syntax node the call expression occupies"
    )
    target_id: str = Field(
        default="", description="identifier of the resolved callee in the dependency graph"
    )
    is_first_party: bool = Field(
        default=False, description="whether the resolved callee lives inside this repository"
    )
