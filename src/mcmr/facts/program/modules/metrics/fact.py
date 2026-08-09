from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact
from .coupling import ModuleCoupling

if TYPE_CHECKING:
    from pydantic import NonNegativeInt


class ModuleCouplingFact(ModuleCoupling, Fact):
    """Describe one module through Robert Martin's package metrics."""

    declaration_count: NonNegativeInt = Field(
        default=0, description="classes this module declares"
    )
    abstract_declaration_count: NonNegativeInt = Field(
        default=0, description="classes this module declares that state an abstract contract"
    )
    dependencies: list[ModuleCoupling] = Field(
        default=[], description="modules this module imports and their own coupling counts"
    )

    @property
    def abstractness(self) -> float:
        """Return the share of module types stating a contract."""
        if not self.declaration_count:
            return 0.0
        return self.abstract_declaration_count / self.declaration_count

    @property
    def distance(self) -> float:
        """Return distance from Martin's main sequence."""
        return abs(self.abstractness + self.instability - 1.0)
