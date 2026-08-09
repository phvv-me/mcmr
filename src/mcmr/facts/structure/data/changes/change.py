from patos import FrozenModel
from pydantic import Field


class DataChange(FrozenModel):
    """Retain one schema change and its transitive impact evidence."""

    asset_identifier: str = Field(description="catalog identifier of the changed asset")
    is_breaking: bool = Field(description="whether the provider declared this change breaking")
    downstream_assets: list[str] = Field(
        default=[], description="identifiers of assets the changed asset's lineage feeds"
    )
    tested_assets: list[str] = Field(
        default=[],
        description="identifiers of assets the change's own retained test evidence covers",
    )
