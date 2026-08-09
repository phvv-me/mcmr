from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import Field, PositiveInt, model_validator

if TYPE_CHECKING:
    from typing import Self


class CloneFragment(FrozenModel):
    """Retain one copy of a repeated fragment and the lines it covers."""

    path: str = Field(description="repository relative path this copy occurs in")
    start_line: PositiveInt = Field(description="first line of this copy, one indexed")
    end_line: PositiveInt = Field(description="last line of this copy, one indexed and inclusive")
    source: str = Field(
        default="", description="literal source text of the lines this copy covers"
    )

    @property
    def line_count(self) -> int:
        """Return the inclusive line count implied by this range."""
        return self.end_line - self.start_line + 1

    @model_validator(mode="after")
    def closes_after_it_opens(self) -> Self:
        """Require one range to end at or after its first line."""
        if self.end_line < self.start_line:
            raise ValueError(
                f"clone fragment ends at line {self.end_line} before line {self.start_line}"
            )
        return self
