from datetime import datetime

from patos import FrozenModel

from .repair import RepairState
from .run import RunState


class RunEvent(FrozenModel):
    """Retain one recorded verdict a receiving system already holds for one rule and subject."""

    at: datetime
    state: RunState
    properties: dict[str, str] = {}

    @property
    def detail(self) -> str:
        """Return the reason this event stated, preferring findings over model reasoning."""
        return self.properties.get("reasons", "") or self.properties.get("reasoning", "")

    @property
    def repair(self) -> RepairState:
        """Return how far the repair got in the run this event records."""
        stated = self.properties.get("repair", "")
        return RepairState(stated) if stated in set(RepairState) else RepairState.NONE
