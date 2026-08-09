from patos import FrozenModel
from pydantic import Field


class EnumMetadataMap(FrozenModel):
    """Retain one literal mapping keyed entirely by members of one local enum."""

    enum_name: str = Field(description="dotted enum the mapping's keys resolve against")
    keys: list[str] = Field(
        default=[], description="dotted enum member names used as the mapping's keys"
    )
    values: list[str] = Field(
        default=[], description="string literal values paired with each key, in mapping order"
    )
    all_keys_resolve_to_enum: bool = Field(
        default=False,
        description="whether every key names a member of one enum and every value is a string",
    )
