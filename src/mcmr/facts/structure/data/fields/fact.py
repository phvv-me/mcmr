from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .reference import DataFieldReference


class DataFieldReferenceFact(Fact):
    """Describe one resolved reference to a data field."""

    external_evidence = True
    references: list[DataFieldReference] = Field(
        default=[], description="field references this literal resolves against the catalog"
    )
