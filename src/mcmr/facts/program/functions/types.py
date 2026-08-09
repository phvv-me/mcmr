from enum import StrEnum, auto

from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class FunctionTypes:
    """Name the structured records embedded in one function fact."""

    class ControlKind(StrEnum):
        """Name one control structure in language-neutral terms."""

        CONDITIONAL = auto()
        ALTERNATIVE = auto()
        LOOP = auto()
        SWITCH = auto()
        CATCH = auto()
        JUMP = auto()
        RECURSION = auto()
        SEQUENCE = auto()

    class ControlIncrement(FrozenModel):
        """Retain one control structure and its nesting depth."""

        kind: FunctionTypes.ControlKind = Field(
            description="language-neutral kind of control structure this increment names"
        )
        nesting_depth: NonNegativeInt = Field(
            default=0, description="how deeply this control structure nests inside others"
        )

    class ParameterIdentity(FrozenModel):
        """Retain one parameter's name, type, and binding position."""

        name: str = Field(description="name the parameter binds")
        type_name: str = Field(default="", description="declared type annotation of the parameter")
        is_positional_only: bool = Field(
            default=False, description="whether the parameter accepts only positional arguments"
        )
        is_keyword_only: bool = Field(
            default=False, description="whether the parameter accepts only keyword arguments"
        )

    class Parameter(ParameterIdentity):
        """Describe one resolved parameter and its call contract."""

        is_receiver: bool = Field(
            default=False, description="whether the parameter is the leading self or cls receiver"
        )
        is_required_by_external_contract: bool = Field(
            default=False,
            description="whether a caller must supply this parameter, no receiver and no default",
        )
        has_boolean_annotation: bool = Field(
            default=False, description="whether the parameter is annotated bool"
        )
        has_boolean_default: bool = Field(
            default=False, description="whether the parameter defaults to a boolean literal"
        )


ControlKind = FunctionTypes.ControlKind
