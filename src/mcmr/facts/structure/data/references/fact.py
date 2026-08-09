from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .reference import DataAssetReference


class DataAssetReferenceFact(Fact):
    """Describe one resolved reference to a governed data asset."""

    external_evidence = True
    references: list[DataAssetReference] = Field(
        default=[], description="asset references this literal resolves against the catalog"
    )
