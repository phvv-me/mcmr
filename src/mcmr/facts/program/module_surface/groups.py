from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from .types import ModuleSurfaceTypes


class ModuleSurfaceFields(Fact):
    """Retain module exports and type-system surface evidence."""

    star_reexports: list[str] = Field(
        default=[],
        description="module specifiers this module wholesale re-exports with export star",
    )
    named_reexport_count: NonNegativeInt = Field(
        default=0, description="named exports this module re-exports from another module"
    )
    export_count: NonNegativeInt = Field(
        default=0, description="named, default, and star export declarations this module states"
    )
    is_index_module: bool = Field(
        default=False, description="whether the module is a barrel file named index.ts"
    )
    deepest_relative_import: NonNegativeInt = Field(
        default=0, description="parent directories the module's deepest relative import climbs"
    )
    deepest_relative_specifier: str = Field(
        default="",
        description="import or re-export specifier that climbs the most parent directories",
    )
    erasable_violations: list[ModuleSurfaceTypes.ErasableConstruct] = Field(
        default=[], description="declarations whose meaning survives TypeScript type stripping"
    )
