from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .edge import DependencyEdge


class DependencyComponentFact(Fact):
    """Describe the import graph of one repository."""

    import_edges: list[DependencyEdge] = Field(
        default=[], description="resolved import edges between modules this repository owns"
    )
