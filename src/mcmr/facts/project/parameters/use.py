from pydantic import Field

from .groups import ParameterUseFields


class ParameterUse(ParameterUseFields):
    """Retain one annotated parameter and every resolved direct operation."""

    operations: list[str] = Field(
        default=[], description="method names and builtin operations invoked on the parameter"
    )
    attribute_reads: list[str] = Field(
        default=[], description="attribute names read directly off the parameter"
    )
    all_uses_known: bool = Field(
        default=True, description="whether every use of the parameter in the body was recognized"
    )
    is_return_value: bool = Field(
        default=False, description="whether the parameter is returned unchanged from the function"
    )
