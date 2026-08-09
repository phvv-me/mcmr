from typing import TYPE_CHECKING

from patos import FrozenModel

from mcmr.plugins import RunState

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Self

    from mcmr.plugins import RunRecord


class ReportedFiles(FrozenModel):
    """Retain which files each rule still reports, once one run has finished judging them.

    A verdict about one file is written when a rule fails there, and nothing writes it again once
    the file is repaired, renamed, or deleted. Only a later run of the same rule can say the file
    is no longer reported, and that one question is asked twice, once to close the verdict and
    once to decide an incident about that file has settled. Both have to answer it the same way,
    and reading the answer back out of the catalog cannot, because a verdict written seconds ago
    is not in the index that would be read.
    """

    executed: set[str] = set()
    failing: set[tuple[str, str]] = set()

    @classmethod
    def of(cls, records: Iterable[RunRecord]) -> Self:
        """Return what one completed run still reports, by the rule and the file it named."""
        stated = list(records)
        return cls(
            executed={record.rule for record in stated},
            failing={
                (record.rule, record.path)
                for record in stated
                if record.state is RunState.FAILURE and record.path
            },
        )

    def settled(self, *, rule: str, path: str) -> bool:
        """Whether this run ran the rule and came back without reporting the file.

        A rule that did not run this time settles nothing, because silence is not a resolution.
        """
        return rule in self.executed and (rule, path) not in self.failing
