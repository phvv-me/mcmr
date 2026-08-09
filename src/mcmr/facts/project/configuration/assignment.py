from typing import Literal

from patos import FrozenModel
from pydantic import Field


class ConfigurationAssignment(FrozenModel):
    """Retain one simple collection assignment from project source."""

    name: str = Field(description="name the collection literal is assigned to")
    collection_kind: Literal["list", "tuple", "set", "other"] = Field(
        description="literal syntax the assigned collection uses"
    )
    values: list[str] = Field(
        default=[], description="literal string elements the collection assignment holds"
    )
    is_typed_configuration_field: bool = Field(
        default=False,
        description="whether the assignment sits inside a class named with a Configuration suffix",
    )
