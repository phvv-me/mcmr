from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class ModuleCoupling(FrozenModel):
    """Retain inward and outward internal module dependency counts."""

    module: str = Field(default="", description="dotted qualified name of the module")
    afferent_count: NonNegativeInt = Field(
        default=0, description="modules that import this module"
    )
    efferent_count: NonNegativeInt = Field(default=0, description="modules this module imports")

    @property
    def instability(self) -> float:
        """Return Martin's share of coupling that points outward."""
        total = self.afferent_count + self.efferent_count
        return self.efferent_count / total if total else 0.0
