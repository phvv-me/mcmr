from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .route import Route


class RouteFact(Fact):
    """Describe every route a repository declares and references."""

    frameworks: list[str] = Field(
        default=[],
        description="route declaration styles found across the repository, such as decorator or "
        "convention",
    )
    routes: list[Route] = Field(default=[], description="every route the repository declares")
