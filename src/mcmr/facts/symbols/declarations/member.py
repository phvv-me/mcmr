from patos import FrozenModel
from pydantic import Field, PositiveInt

from .parameter import ParameterDeclaration


class MemberDeclaration(FrozenModel):
    """Retain a member exactly as its owning class writes it down."""

    name: str = Field(default="", description="name of the declared member")
    parameters: list[ParameterDeclaration] | None = Field(
        default=None, description="declared parameters, absent when the member is an attribute"
    )
    decorators: list[str] = Field(
        default=[], description="decorator expressions applied to the member"
    )
    asynchronous: bool = Field(default=False, description="whether the member is declared async")
    line: PositiveInt = Field(default=1, description="source line where the member is declared")
    source: str = Field(default="", description="verbatim source text of the member declaration")
