from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .citation import ManuscriptCitation
    from .number import ManuscriptNumber
    from .reference import ManuscriptReference


class ManuscriptEvidenceFact(Fact):
    """Describe the numbers one manuscript states and the sources it leans on."""

    root: str = Field(default="", description="file a build of this manuscript is pointed at")
    numbers: list[ManuscriptNumber] = Field(
        default=[], description="every number the manuscript prints, in reading order"
    )
    citations: list[ManuscriptCitation] = Field(
        default=[], description="every bibliography reference, in reading order"
    )
    references: list[ManuscriptReference] = Field(
        default=[],
        description="every cross reference, so a number can be read against what its section cites",
    )
