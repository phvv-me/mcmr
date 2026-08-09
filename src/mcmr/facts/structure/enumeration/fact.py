from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .analysis import EnumAnalysis
    from .context.file import EnumFile
    from .context.scope import EnumScope


class Enum(Fact):
    """Describe enumerations, their members, scopes, and files."""

    enums: list[EnumAnalysis] = Field(
        default=[], description="enum classes this repository declares"
    )
    scopes: list[EnumScope] = Field(
        default=[], description="candidate shared modules for enums reused across a narrow package"
    )
    files: list[EnumFile] = Field(
        default=[], description="files under an enums directory and their declaration shape"
    )
