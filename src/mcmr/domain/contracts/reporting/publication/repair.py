from enum import StrEnum, auto


class RepairState(StrEnum):
    """State how far one run carried the repair a failing rule offered."""

    NONE = auto()
    OFFERED = auto()
    PREVIEWED = auto()
    APPLIED = auto()
    REFUSED = auto()
