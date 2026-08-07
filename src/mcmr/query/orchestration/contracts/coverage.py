from patos import Model

from ....domain.contracts import RunGraph
from ....kernel import KernelStats


class TableCoverage(Model):
    """Report what one table execution reached across the analyzed repository."""

    kernel: KernelStats = KernelStats()
    runnable: set[str] = set()
    languages: set[str] = set()
    read_families: set[str] = set()
    graph: RunGraph = RunGraph()

    @property
    def provider_read_count(self) -> int:
        """Return how many distinct fact families the selected rules read."""
        return len(self.read_families)

    def completed(self, kernel: KernelStats, graph: RunGraph) -> TableCoverage:
        """Retain what the whole run measured and consumed once its last batch finished."""
        self.kernel = kernel
        self.graph = graph
        return self
