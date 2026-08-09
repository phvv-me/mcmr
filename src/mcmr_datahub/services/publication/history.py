from patos import FrozenModel

from mcmr.plugins import NonEmptyStr


class SubjectHistory(FrozenModel):
    """Retain what one file's recorded verdicts did inside the window a catalog still holds.

    A rule that fails, passes, and fails again at the same file is telling a reader something a
    rule that simply keeps failing is not. Either the rule reads something that moves underneath
    it or the problem itself keeps coming back, and both deserve a person rather than another
    line in a report nobody reads twice.
    """

    rule: NonEmptyStr
    path: NonEmptyStr
    subject: NonEmptyStr
    changes: int = 0
    failing: bool = False
    alternates: bool = False
    timeline: list[str] = []

    @property
    def description(self) -> str:
        """Return what the recorded window actually showed, in the order it showed it."""
        observed = ", then ".join(self.timeline)
        return (
            f"{self.rule} turned off and on at {self.path} across the recorded window, changing "
            f"verdict {self.changes} times. The runs read {observed}. A rule that only sometimes "
            f"reports a file is either reading something that moves underneath it or reporting a "
            f"problem that keeps coming back, and neither is answered by running the check again."
        )

    @property
    def title(self) -> str:
        """Return the one title this subject's incident keeps, which is how it is recognized."""
        return f"{self.rule} is intermittent at {self.path}"

    def resolution(self, run: str) -> str:
        """Return what closes this incident, which names the run that steadied the subject."""
        return (
            f"Run {run} recorded {self.rule} passing at {self.path}, so the off and on pattern "
            f"this incident was raised for has stopped."
        )
