from typing import TYPE_CHECKING

from pydantic import Field

from .groups import ExportBypassFields

if TYPE_CHECKING:
    from ....foundation import SourceSpan


class ExportBypass(ExportBypassFields):
    """Retain an import that bypasses a shorter explicit package export."""

    is_cycle_safe: bool = Field(
        default=False,
        description="whether rewriting this bypass to the public route stays cycle free",
    )
    span: SourceSpan = Field(description="source location of the bypassing import statement")
