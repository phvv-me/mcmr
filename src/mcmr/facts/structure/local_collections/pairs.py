from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class PairSequence(FrozenModel):
    """Retain one literal pair sequence and its lookup-only reads."""

    pair_count: NonNegativeInt = Field(description="number of two-element pairs the literal holds")
    keys_are_unique_literals: bool = Field(
        description="whether every pair's key is a literal of one kind, each key text unique"
    )
    has_single_assignment: bool = Field(
        description="whether the binding is assigned to exactly once"
    )
    all_reads_are_lookup_loops: bool = Field(
        description="whether every read is a loop returning the value for its matched key"
    )
