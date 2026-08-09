from typing import Literal

from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class LocalCollection(FrozenModel):
    """Retain one local collection and its representation-sensitive uses."""

    name: str = Field(default="", description="local variable name the collection is bound to")
    kind: Literal["list", "tuple"] = Field(
        description="literal shape the collection is written as"
    )
    value_count: NonNegativeInt = Field(description="number of elements the literal holds")
    has_homogeneous_literals: bool = Field(
        description="whether every element is a literal of the same kind"
    )
    all_reads_are_iteration: bool = Field(
        default=False, description="whether every read of the binding iterates over it"
    )
    all_reads_are_membership: bool = Field(
        default=False, description="whether every read of the binding is an `in` membership test"
    )
    values_are_unique: bool = Field(
        default=False, description="whether every element's source text is distinct"
    )
