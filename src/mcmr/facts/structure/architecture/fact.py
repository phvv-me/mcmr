from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .characteristic import ArchitectureCharacteristic


class ArchitectureCharacteristicFact(Fact):
    """Describe one declared architecture characteristic and its evidence."""

    characteristics: list[ArchitectureCharacteristic] = Field(
        default=[], description="declared architecture characteristics this fact retains"
    )
