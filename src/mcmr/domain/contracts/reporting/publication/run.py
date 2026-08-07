from enum import StrEnum, auto


class RunState(StrEnum):
    """State whether one rule held, failed, or could not answer for one subject."""

    SUCCESS = auto()
    FAILURE = auto()
    ERROR = auto()
