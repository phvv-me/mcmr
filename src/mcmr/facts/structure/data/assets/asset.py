from typing import Literal

from patos import FrozenModel
from pydantic import Field

from .field import DataField


class DataAsset(FrozenModel):
    """Retain one catalog asset and its governance metadata."""

    identifier: str = Field(description="catalog identifier, typically a DataHub URN")
    description: str = Field(default="", description="business description the catalog records")
    owners: list[str] = Field(
        default=[], description="identity of each owner the catalog's ownership aspect records"
    )
    domain: str = Field(
        default="", description="human readable domain name the catalog assigns the asset"
    )
    lifecycle: Literal["active", "deprecated", "removed", "unknown"] = Field(
        default="unknown", description="lifecycle state the catalog declares for the asset"
    )
    is_changed: bool = Field(
        default=False,
        description="whether the catalog reports the asset modified after the configured cutoff",
    )
    fields: list[DataField] = Field(
        default=[], description="schema fields the catalog records for the asset"
    )
