from patos import FrozenModel
from pydantic import Field

from .kind import ParameterKind


class ParameterDeclaration(FrozenModel):
    """Retain a parameter exactly as its declaration writes it down."""

    name: str = Field(default="", description="name of the declared parameter")
    kind: ParameterKind = Field(
        default=ParameterKind.POSITIONAL_OR_KEYWORD,
        description="how the parameter binds a caller's argument",
    )
    has_default: bool = Field(
        default=False, description="whether the parameter declares a default value"
    )
