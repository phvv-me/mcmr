from patos import FrozenModel
from pydantic import Field, PositiveInt


class InteropReference(FrozenModel):
    """Retain one place naming a cross-language artifact."""

    path: str = Field(
        description="repository relative path of the file that references the artifact"
    )
    language: str = Field(description="language of the file that references the artifact")
    line: PositiveInt = Field(default=1, description="line number where the reference occurs")
