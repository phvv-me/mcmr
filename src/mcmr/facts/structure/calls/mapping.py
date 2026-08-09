from patos import FrozenModel
from pydantic import Field

from .expression import Expression


class MappingEntry(FrozenModel):
    """Retain one key and value of a directly stated literal mapping."""

    key: str = Field(description="literal key text of the mapping entry")
    value: Expression = Field(description="expression bound to the key")
