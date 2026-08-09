from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .access import AttributeAccess


class AttributeAccessFact(Fact):
    """Describe one resolved attribute access and its owning scope."""

    accesses: list[AttributeAccess] = Field(
        default=[], description="resolved attribute accesses this fact retains"
    )
