from patos import FrozenModel
from pydantic import Field

from .repair import DataFieldRepair


class DataFieldReference(FrozenModel):
    """Retain one source field reference, exact schema resolution, and any proven repair."""

    asset_identifier: str = Field(description="catalog identifier of the referenced asset")
    field_name: str = Field(description="column name the source literal references")
    asset_exists: bool = Field(description="whether the referenced asset resolves in the catalog")
    field_exists: bool = Field(
        description="whether the catalog schema for the asset declares this field"
    )
    expected_type: str = Field(
        default="",
        description="type the source casts the field to, when it disagrees with the catalog",
    )
    catalog_type: str = Field(
        default="", description="type the catalog schema declares for the field, when it exists"
    )
    repair: DataFieldRepair = Field(
        default=DataFieldRepair(),
        description="literal rewrite a catalog proven rename licenses, when one exists",
    )
