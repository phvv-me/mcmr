from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .enum import EnumMetadataMap
    from .string import StringLiteralGroup


class LiteralGroupFact(Fact):
    """Describe one group of equal or structurally related literals."""

    string_groups: list[StringLiteralGroup] = Field(
        default=[], description="repeated equal string literals grouped by resolved syntax role"
    )
    enum_metadata_maps: list[EnumMetadataMap] = Field(
        default=[], description="literal mappings keyed entirely by members of one local enum"
    )
