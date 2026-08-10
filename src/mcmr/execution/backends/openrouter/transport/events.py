from collections.abc import Callable
from enum import StrEnum, auto


class StreamPhase(StrEnum):
    """Name the observable phases of one streamed model response."""

    CONNECTED = auto()
    REASONING = auto()
    GENERATING = auto()
    RETRYING = auto()
    COMPLETED = auto()


type StreamObserver = Callable[[StreamPhase, int], None]
