from patos import FrozenModel
from pydantic import Field

from .expression import Expression


class MappingEntry(FrozenModel):
    """Retain one item of a directly stated literal mapping, keyed or unpacked."""

    key: str = Field(description="literal key text of the mapping entry, empty when unpacked")
    is_spread: bool = Field(
        default=False, description="whether the item unpacks another mapping instead of a key"
    )
    value: Expression = Field(description="expression bound to the key, or the unpacked mapping")
