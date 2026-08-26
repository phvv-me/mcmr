from patos import FrozenModel
from pydantic import Field, NonNegativeInt, PositiveInt

from ...foundation import SourceSpan


class ManuscriptPlace(FrozenModel):
    """Locate one manuscript record in the file a reader would open to change it."""

    reading_order: NonNegativeInt = Field(
        default=0, description="index of this record in the assembled reading order"
    )
    path: str = Field(default="", description="repository relative file the record was read from")
    line: PositiveInt = Field(default=1, description="line the record was read from")
    section_number: NonNegativeInt = Field(
        default=0,
        description="section holding this record counted from one, zero when it sits in none",
    )

    @property
    def span(self) -> SourceSpan:
        """Locate this record where its own file states it."""
        return SourceSpan(path=self.path, start_line=self.line)
