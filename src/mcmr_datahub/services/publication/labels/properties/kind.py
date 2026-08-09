from enum import StrEnum, auto


class PropertyKind(StrEnum):
    """Name the value domain one typed property stores."""

    STRING = auto()
    NUMBER = auto()
