from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .....domain.contracts import RuleTimeline
    from .history import HistoryContext


@runtime_checkable
class RunHistoryReader(Protocol):
    """Read back the verdicts a provider already recorded for the subjects it governs.

    A provider opts in beside `FactProvider` so an agent can ask what previous runs concluded
    before it changes anything. Reading history never judges and never writes.
    """

    async def history(self, context: HistoryContext) -> list[RuleTimeline]: ...
