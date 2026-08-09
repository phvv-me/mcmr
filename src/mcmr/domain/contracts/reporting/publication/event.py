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

    @property
    def tokens(self) -> int:
        """Return what the model turns behind this recorded verdict cost, in tokens.

        A deterministic verdict states no token count at all, which reads as the nothing it spent
        rather than as a missing measurement.
        """
        counted = (
            self.properties.get(name, "")
            for name in ("inputTokens", "cachedInputTokens", "outputTokens")
        )
        return sum(int(value) for value in counted if value.isdigit())
