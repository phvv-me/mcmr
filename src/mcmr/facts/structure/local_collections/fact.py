from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .local import LocalCollection
    from .pairs import PairSequence


class CollectionFact(Fact):
    """Describe one collection expression and its uses."""

    pair_sequences: list[PairSequence] = Field(
        default=[], description="fixed pair sequences a callable body binds and reads by key"
    )
    local_collections: list[LocalCollection] = Field(
        default=[], description="local list or tuple literals a callable body binds exactly once"
    )
