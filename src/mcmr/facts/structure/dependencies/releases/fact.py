from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .record import DependencyRecord


class DependencyFact(Fact):
    """Describe one selected dependency and its release metadata."""

    external_evidence = True
    dependencies: list[DependencyRecord] = Field(
        default=[], description="resolved dependency records and their release metadata"
    )
