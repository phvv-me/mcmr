from patos import FrozenModel
from pydantic import Field


class LineageEdge(FrozenModel):
    """Retain one directed lineage edge and exact endpoint resolution."""

    source: str = Field(description="identifier of the upstream data asset the edge starts from")
    target: str = Field(description="identifier of the downstream data asset the edge reaches")
    source_exists: bool = Field(
        description="whether the source identifier resolves to a cataloged asset"
    )
    target_exists: bool = Field(
        description="whether the target identifier resolves to a cataloged asset"
    )
