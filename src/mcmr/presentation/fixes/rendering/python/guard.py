from typing import TYPE_CHECKING

from .....domain.errors import UnrenderableFix
from .parsing import parse_python
from .values import CarriedValues

if TYPE_CHECKING:
    import ast
    from collections import Counter

    from .....facts.foundation import NodeRef, SourceSpan
    from ..documents import SourceDocument


class ReplacementGuard:
    """Prove one replacement still states every value and unpacking its target supplied."""

    def __init__(self, document: SourceDocument, target: NodeRef, source: str) -> None:
        self.document = document
        self.target = target
        self.source = source

    def require_carried(self) -> None:
        """Refuse replacement source that drops a value or an unpacking its target supplied."""
        supplied = CarriedValues(self._parsed(self.document.text), self.target.span)
        written = CarriedValues(self._parsed(self._revised()), self._written_region())
        self._require_kept(supplied.data_names - written.stated_names, kind="value")
        self._require_kept(supplied.unpackings - written.unpackings, kind="unpacking")

    def _parsed(self, source: str) -> ast.Module:
        """Parse one whole module so every name reads in the position its own file gives it."""
        return parse_python(source, path=self.document.path)

    def _require_kept(self, dropped: Counter[str], *, kind: str) -> None:
        """Refuse a replacement whose own source no longer states what the target did."""
        if dropped:
            stated = ", ".join(f"`{item}`" for item in sorted(dropped))
            raise UnrenderableFix(
                f"the replacement for {self.target.id} drops the {kind} {stated} that "
                f"{self.target.text!r} supplies"
            )

    def _revised(self) -> str:
        """Return the whole module as this one replacement alone would leave it."""
        start, end = self.document.node_range(self.target)
        revised = (
            self.document.original[:start]
            + self.source.encode("utf-8")
            + self.document.original[end:]
        )
        return revised.decode("utf-8")

    def _written_region(self) -> SourceSpan:
        """Return the span the replacement source occupies once it is written."""
        lines = self.source.encode("utf-8").split(b"\n")
        span = self.target.span
        return span.model_copy(
            update={
                "end_line": span.start_line + len(lines) - 1,
                "end_column": len(lines[-1])
                if len(lines) > 1
                else span.start_column + len(lines[0]),
            }
        )
