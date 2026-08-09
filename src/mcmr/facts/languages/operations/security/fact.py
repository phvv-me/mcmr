from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .boundary import SecurityBoundary


class SecurityBoundaryFact(Fact):
    """Describe security boundaries and their threat-model evidence."""

    boundaries: list[SecurityBoundary] = Field(
        default=[], description="security boundaries and their threat-model evidence"
    )
