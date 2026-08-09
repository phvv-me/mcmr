from typing import TYPE_CHECKING

from patos import FrozenModel

from ....primitives import NonEmptyStr
from .event import RunEvent
from .repair import RepairState
from .run import RunState

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


class RuleTimeline(FrozenModel):
    """Retain every recorded verdict one rule reached about one subject, oldest first."""

    rule: NonEmptyStr
    subject: NonEmptyStr
    summary: str = ""
    events: list[RunEvent] = []

    @property
    def last_failure(self) -> str:
        """Return the reason of the most recent failure, which is what an agent reads first."""
        failures = [event for event in self.events if event.state is RunState.FAILURE]
        return failures[-1].detail if failures else ""

    @property
    def repairs(self) -> int:
        """Return how many recorded runs carried a repair all the way to an applied edit."""
        return sum(event.repair is RepairState.APPLIED for event in self.events)

    @property
    def since(self) -> datetime | None:
        """Return when the current state began, which is the run that last changed it."""
        return self._current[0].at if self._current else None

    @property
    def state(self) -> RunState:
        """Return the verdict the most recent recorded run reached."""
        return self.events[-1].state if self.events else RunState.ERROR

    @property
    def tokens(self) -> int:
        """Return what every recorded run of this rule has cost here, in tokens."""
        return sum(event.tokens for event in self.events)

    @property
    def where(self) -> str:
        """Return the file this timeline is about, which only a source subject carries.

        A fact table holds one timeline per file a rule reported beside the repository-wide one,
        so the file is what tells them apart on screen.
        """
        located = [event.properties.get("path", "") for event in self.events]
        return next((path for path in reversed(located) if path), "")

    @property
    def _current(self) -> Sequence[RunEvent]:
        """Return the unbroken tail of events sharing the latest state."""
        unbroken: list[RunEvent] = []
        for event in reversed(self.events):
            if event.state is not self.state:
                break
            unbroken.insert(0, event)
        return unbroken
