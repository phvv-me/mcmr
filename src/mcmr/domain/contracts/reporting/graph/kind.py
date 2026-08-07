from enum import StrEnum, auto


class ColumnType(StrEnum):
    """Name the value domain one flattened fact column stores."""

    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
