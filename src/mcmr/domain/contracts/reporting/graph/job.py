from patos import FrozenModel

from ....primitives import NonEmptyStr
from .spend import ModelSpend
from .tables import RuleTables


class RuleJob(FrozenModel):
    """State one executed rule as the job that read its declared fact datasets."""

    rule: NonEmptyStr
    callable: str = ""
    summary: str = ""
    tables: RuleTables = RuleTables()
    lanes: list[str] = []
    family: str = ""
    spend: dict[str, ModelSpend] = {}

    @property
    def lane(self) -> str:
        """Return the one lane a reader is told this rule belongs to.

        A rule can need both a model and a network, and the model is what a reader has to know
        first, so the lanes stay a list while the label leading them is the strongest one.
        """
        return self.lanes[0] if self.lanes else ""

    @property
    def spent(self) -> ModelSpend:
        """Return what every model turn this rule paid for cost, across every file it read."""
        return ModelSpend.of(self.spend.values())
