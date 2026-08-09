from typing import Literal

from patos import FrozenModel
from pydantic import Field


class DataAssetReference(FrozenModel):
    """Retain one source reference and its exact catalog resolution."""

    source_location: str = Field(description="exact source location the reference was read from")
    asset_identifier: str = Field(
        description="resolved catalog identifier, or the literal text when unresolved"
    )
    asset_exists: bool = Field(description="whether the identifier resolves in the catalog")
    lifecycle: Literal["active", "deprecated", "removed", "unknown"] = Field(
        default="unknown",
        description="lifecycle state the catalog declares for the resolved asset",
    )
    upstream_health: dict[str, Literal["healthy", "unhealthy", "unknown"]] = Field(
        default_factory=dict,
        description="quality evidence for each asset upstream of this one, keyed by identifier",
    )
