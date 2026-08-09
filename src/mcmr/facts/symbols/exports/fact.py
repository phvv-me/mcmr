from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .entries.bypass import ExportBypass
    from .entries.public import PublicExport


class ExportFact(Fact):
    """Describe one explicit public name and its repository consumers."""

    public_export: PublicExport = Field(
        description="the explicit public export this fact describes"
    )
    bypasses: list[ExportBypass] = Field(
        default=[],
        description="imports elsewhere in the repository that reach this export's target directly",
    )
