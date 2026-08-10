from collections import Counter
from functools import partial
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from .events import StreamObserver, StreamPhase

if TYPE_CHECKING:
    from types import TracebackType


class RepositoryProgress:
    """Render honest request completion and live streamed response activity."""

    def __init__(self, total: int) -> None:
        console = Console(stderr=True)
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.fields[received]} received"),
            console=console,
            disable=not console.is_terminal,
        )
        self.task = self.progress.add_task("DeepSeek waiting", total=total, received="0 B")
        self.states: dict[int, StreamPhase] = {}
        self.received = 0

    def __enter__(self) -> RepositoryProgress:
        self.progress.start()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.progress.stop()

    def observer(self, request: int) -> StreamObserver:
        """Return the event sink for one planned repository request."""
        return partial(self._observe, request)

    @staticmethod
    def _size(received: int) -> str:
        """Render received response bytes without pretending they are model tokens."""
        return f"{received / 1_000_000:.1f} MB" if received >= 1_000_000 else f"{received:,} B"

    def _observe(self, request: int, phase: StreamPhase, received: int) -> None:
        """Update one aggregate bar from a response stream event."""
        self.received += received
        advance = 0
        if phase is StreamPhase.COMPLETED:
            self.states.pop(request, None)
            advance = 1
        else:
            self.states[request] = phase
        activity = Counter(self.states.values())
        labels = " ".join(
            f"{count} {phase}"
            for phase, count in sorted(activity.items(), key=lambda item: str(item[0]))
        )
        self.progress.update(
            self.task,
            advance=advance,
            description=f"DeepSeek {labels or 'finishing'}",
            received=self._size(self.received),
        )
