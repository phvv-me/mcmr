from patos import FrozenModel

from .dataset import FactDataset
from .job import RuleJob
from .spend import ModelSpend


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
        return {job.rule: job.tables.primary for job in self.jobs if job.tables.primary}

    @property
    def lane_counts(self) -> dict[str, int]:
        """Return how many executed rules each lane claims, a rule in two lanes counting in both.

        This is what a run history answers when a reader asks what kind of work a run actually
        did, which is a different question from how many rules the catalog holds.
        """
        counted: dict[str, int] = {}
        for job in self.jobs:
            for lane in job.lanes:
                counted[lane] = counted.get(lane, 0) + 1
        return counted

    @property
    def spent(self) -> ModelSpend:
        """Return what the contextual lane cost across this run, which is nothing when it slept."""
        return ModelSpend.of(job.spent for job in self.jobs)

    def anchor(self, rule: str) -> str:
        """Return the dataset one rule's verdicts anchor on, or nothing when it read none."""
        return self.anchors.get(rule, "")

    def lane(self, rule: str) -> str:
        """Return the lane one rule answered in, which is what a recorded verdict states."""
        return next((job.lane for job in self.jobs if job.rule == rule), "")

    def spend(self, rule: str, *, path: str = "") -> ModelSpend:
        """Return what one rule's model turns cost, at one file or across every file it read.

        A verdict about one file was reached by the turns that read that file, so naming the file
        states what that verdict alone cost rather than what the rule cost everywhere.
        """
        job = next((item for item in self.jobs if item.rule == rule), None)
        if job is None:
            return ModelSpend()
        return job.spend.get(path, ModelSpend()) if path else job.spent
