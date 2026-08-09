from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .asset import DataAsset


class DataAssetFact(Fact):
    """Describe one governed data asset."""

    external_evidence = True
    assets: list[DataAsset] = Field(
        default=[], description="catalog assets this bounded snapshot retains"
    )
