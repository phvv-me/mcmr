from patos import FrozenModel

from .dataset import FactDataset
from .job import RuleJob


class RunGraph(FrozenModel):
    """State the fact tables one run consumed and the rules that read them.

    A run already knows which families it materialized, how many rows each carried, and which
    rule declared which of them, so publishing that graph costs no second analysis. It is also
    what lets a verdict about ordinary source anchor somewhere a catalog can hold it, since the
    dataset a rule reads is the closest thing the run has to the subject it judged.
    """

    repository: str = ""
    source: str = ""
    datasets: list[FactDataset] = []
    jobs: list[RuleJob] = []

    @property
    def anchors(self) -> dict[str, str]:
        """Return the dataset every executed rule anchors its verdicts on, by rule identity."""
        return {job.rule: job.primary for job in self.jobs if job.primary}

    def anchor(self, rule: str) -> str:
        """Return the dataset one rule's verdicts anchor on, or nothing when it read none."""
        return self.anchors.get(rule, "")
