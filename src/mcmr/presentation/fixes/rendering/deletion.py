from enum import StrEnum, auto
from typing import TYPE_CHECKING

from ....facts import MemberKind

if TYPE_CHECKING:
    from typing import Self

# The kinds that carry their own blank separator, so removing one takes the separator with it.
_SEPARATED = {
    MemberKind.CONSTRUCTOR,
    MemberKind.DESTRUCTOR,
    MemberKind.PROPERTY,
    MemberKind.STATIC_METHOD,
    MemberKind.CLASS_METHOD,
    MemberKind.METHOD,
}

# The kinds a language writes with blank lines under them, which belong to the declaration above.
_BLOCK = {"comment", "comment-group", "function", "import"}


class DeletionShape(StrEnum):
    """Say how much of a document one kind of node takes with it when it is removed.

    A document knows byte offsets and line endings and nothing about what a constructor is. This
    is the one place that reads a node kind, so adding a language whose members are separated
    differently is an edit here rather than inside the offset arithmetic.
    """

    ITEM = auto()
    LINE = auto()
    BLOCK = auto()
    SEPARATED = auto()

    @classmethod
    def of(cls, kind: str) -> Self:
        """Return what removing one node of this kind reaches beyond the node itself."""
        if kind == "sequence-item":
            return cls(cls.ITEM)
        if kind in _SEPARATED:
            return cls(cls.SEPARATED)
        return cls(cls.BLOCK) if kind in _BLOCK else cls(cls.LINE)
