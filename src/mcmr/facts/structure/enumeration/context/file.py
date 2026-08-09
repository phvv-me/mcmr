from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class EnumFile(FrozenModel):
    """Retain the shape and reuse of one file under an enums directory."""

    path: str = Field(description="repository relative path of the file")
    top_level_class_count: NonNegativeInt = Field(
        description="number of top-level classes the file declares"
    )
    enum_class_count: NonNegativeInt = Field(
        description="top-level classes the file declares that derive from a configured enum base"
    )
    is_package_initializer: bool = Field(
        default=False, description="whether the file is the package's `__init__.py`"
    )
    is_shared_across_unrelated_branches: bool = Field(
        default=False,
        description="whether declarations here are imported from two or more unrelated branches",
    )
