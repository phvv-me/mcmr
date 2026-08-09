from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Relation

if TYPE_CHECKING:
    from pydantic import NonNegativeInt, PositiveInt


class DependencyEdge(Relation):
    """Retain one resolved import between repository-owned modules."""

    path: str = Field(default="", description="repository relative path of the importing module")
    line: PositiveInt = Field(default=1, description="line number the import statement occupies")
    source_component: NonNegativeInt = Field(
        default=0,
        description="identifier of the strongly connected component holding the importing module",
    )
    target_component: NonNegativeInt = Field(
        default=0,
        description="identifier of the strongly connected component holding the imported module",
    )
