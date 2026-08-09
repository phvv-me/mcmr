from patos import FrozenModel
from pydantic import Field


class DataField(FrozenModel):
    """Retain one catalog field, its documented type, and its governance labels."""

    name: str = Field(description="field path the catalog schema declares")
    data_type: str = Field(description="type the catalog schema records for the field")
    description: str = Field(
        default="", description="business description the catalog records for the field"
    )
    tags: list[str] = Field(default=[], description="tag labels the catalog attaches to the field")
    glossary_terms: list[str] = Field(
        default=[], description="glossary term labels the catalog attaches to the field"
    )
