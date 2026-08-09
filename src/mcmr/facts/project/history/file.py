from patos import FrozenModel
from pydantic import Field, NonNegativeInt, PositiveInt

from ....domain.primitives import NonEmptyStr


class FileHistory(FrozenModel):
    """Retain how often one file changed, by how many hands, and how long ago."""

    path: NonEmptyStr = Field(description="repository relative path the file history describes")
    author_count: PositiveInt = Field(
        default=1, description="distinct commit authors who changed the file"
    )
    additional_commit_count: NonNegativeInt = Field(
        default=0, description="commits touching the file beyond one per distinct author"
    )
    days_since_last_change: NonNegativeInt = Field(
        default=0, description="days since the file's most recent commit, from the newest commit"
    )
    line_count: NonNegativeInt = Field(
        default=0, description="current line count of the file's contents"
    )
    is_test: bool = Field(
        default=False, description="whether the file's path is recognized as a test path"
    )
    imports: list[str] = Field(
        default=[], description="modules the file's source lexically imports"
    )

    @property
    def commit_count(self) -> int:
        """Return all file commits without storing an impossible author relationship."""
        return self.author_count + self.additional_commit_count
