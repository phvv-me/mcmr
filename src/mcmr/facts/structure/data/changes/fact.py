from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .change import DataChange


class DataChangeFact(Fact):
    """Describe one schema or contract change affecting data."""

    external_evidence = True
    changes: list[DataChange] = Field(
        default=[], description="schema or contract changes this bounded snapshot retains"
    )
