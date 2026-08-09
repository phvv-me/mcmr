from typing import TYPE_CHECKING

from pydantic import Field

from .groups import MethodAnalysisFields

if TYPE_CHECKING:
    from collections.abc import Sequence


class MethodAnalysis(MethodAnalysisFields):
    """Retain ordering and binding facts for one declared method."""

    is_protocol_name: bool = Field(
        default=False, description="whether the method name matches a recognized dunder protocol"
    )
    reads_receiver: bool = Field(
        default=False, description="whether an ordinary or class bound method reads its receiver"
    )
    reads_receiver_state: bool = Field(
        default=False, description="whether the method reads state off the receiver it declares"
    )
    owner_qualified_calls: list[str] = Field(
        default=[],
        description="sibling methods this method calls through the owning class's literal name",
    )

    def order_key(
        self,
        *,
        lifecycle: Sequence[str],
        visibility_order: Sequence[str],
        kind_order: Sequence[str],
        alphabetical: bool,
    ) -> tuple[int, int, int, str]:
        """Return this method's position under one declared member order."""
        if self.name in lifecycle:
            return (0, lifecycle.index(self.name), 0, "")
        if self.is_protocol_name:
            return (1, 0, 0, self.name.casefold() if alphabetical else "")
        return (
            2,
            self._rank(visibility_order, self.visibility),
            self._rank(kind_order, self.kind),
            self.name.casefold() if alphabetical else "",
        )

    @staticmethod
    def _rank(order: Sequence[str], value: str) -> int:
        """Return a value's declared position or the trailing position."""
        return order.index(value) if value in order else len(order)
