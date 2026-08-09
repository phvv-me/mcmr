from patos import FrozenModel
from pydantic import Field, PositiveInt

from ...foundation import SourceSpan
from .reference import RouteReference


class Route(FrozenModel):
    """Retain one declared route and every literal naming its path."""

    method: str = Field(description="HTTP verb the route is declared for, such as get or post")
    path: str = Field(description="path the route serves")
    framework: str = Field(
        description="how the route was declared, such as decorator, registration, or convention"
    )
    declared_in: str = Field(
        description="repository relative path of the file that declares the route"
    )
    line: PositiveInt = Field(default=1, description="line the route is declared on")
    is_prefix_composed: bool = Field(
        default=False,
        description="whether a mounted router composes an additional prefix onto this path",
    )
    references: list[RouteReference] = Field(
        default=[], description="other source locations naming this route's path as a literal"
    )

    @property
    def span(self) -> SourceSpan:
        """Locate this route where its framework declares it."""
        return SourceSpan(path=self.declared_in, start_line=self.line)
