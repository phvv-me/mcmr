from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class EnumScope(FrozenModel):
    """Retain enum reuse inside one narrow common package."""

    destination: str = Field(description="dotted module path proposed as the shared enums module")
    enum_count: NonNegativeInt = Field(
        description="number of enum declarations assigned to this scope"
    )
    reused_enum_count: NonNegativeInt = Field(
        description="this scope's enum declarations that are imported outside their own module"
    )
    cross_module_import_count: NonNegativeInt = Field(
        description="number of times this scope's reused enums are imported across modules"
    )
