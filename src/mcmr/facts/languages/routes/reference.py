from patos import FrozenModel
from pydantic import Field, PositiveInt

from ...foundation import SourceSpan


class RouteReference(FrozenModel):
    """Retain one literal reference to a route path."""

    path: str = Field(
        description="repository relative path of the file naming the route as a literal"
    )
    language: str = Field(description="language of the file naming the route")
    line: PositiveInt = Field(default=1, description="line the route path literal appears on")

    @property
    def span(self) -> SourceSpan:
        """Locate this literal reference in its source file."""
        return SourceSpan(path=self.path, start_line=self.line)
