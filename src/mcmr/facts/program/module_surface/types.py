from typing import Literal

from patos import FrozenModel
from pydantic import Field, PositiveInt


class ModuleSurfaceTypes:
    """Own the compact value models nested under one module surface fact."""

    class ErasableConstruct(FrozenModel):
        """Retain one construct surviving type stripping."""

        kind: Literal["enum", "const_enum", "namespace", "parameter_property", "import_equals"] = (
            Field(description="kind of declaration that survives TypeScript type stripping")
        )
        name: str = Field(default="", description="name the declaration binds")
        line: PositiveInt = Field(
            default=1, description="line number where the declaration occurs"
        )

    class EscapeHatch(FrozenModel):
        """Retain one place stepping around proven type information."""

        kind: Literal["assertion", "non_null", "any", "ignore_comment"] = Field(
            description="kind of type-system escape hatch"
        )
        line: PositiveInt = Field(
            default=1, description="line number where the escape hatch occurs"
        )
