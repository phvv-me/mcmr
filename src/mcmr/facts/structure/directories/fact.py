from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from ....domain.primitives import NonEmptyStr


class DirectoryFact(Fact):
    """Describe one project directory and its unignored entries."""

    entry_count: NonNegativeInt = Field(
        default=0, description="number of unignored direct entries this directory holds"
    )
    source_depth: NonNegativeInt = Field(
        default=0,
        description="directory levels between this directory and the source root above it",
    )
    direct_file_count: NonNegativeInt = Field(
        default=0,
        description="unignored files directly inside this directory, excluding a package init",
    )
    direct_directory_count: NonNegativeInt = Field(
        default=0, description="unignored subdirectories directly inside this directory"
    )
    only_child_directory: NonEmptyStr | None = Field(
        default=None,
        description="name of the sole subdirectory, when this directory holds exactly one",
    )
    direct_module_count: NonNegativeInt = Field(
        default=0,
        description="source modules directly inside this directory, excluding a package init",
    )
    is_definition_catalog: bool = Field(
        default=False,
        description="whether every module directly here declares exactly one thing",
    )
