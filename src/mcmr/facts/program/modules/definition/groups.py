from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from .constant import ConstantPlacement


class ModuleFields(Fact):
    """Retain module size, declaration, and package identity fields."""

    constant_placements: list[ConstantPlacement] = Field(
        default=[], description="public module constants and statements before their valid anchor"
    )
    physical_line_count: NonNegativeInt = Field(
        default=0, description="total lines of source text in the module"
    )
    statement_count: NonNegativeInt = Field(
        default=0, description="total statements the module's syntax tree walks"
    )
    class_count: NonNegativeInt = Field(
        default=0, description="top-level classes the module declares"
    )
    function_count: NonNegativeInt = Field(
        default=0, description="top-level functions the module declares"
    )
    executable_statement_count: NonNegativeInt = Field(
        default=0, description="top-level statements the module holds excluding its docstring"
    )
    is_package_initializer: bool = Field(
        default=False, description="whether the module is a package's __init__.py"
    )
