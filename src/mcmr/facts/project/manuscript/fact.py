from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .float import ManuscriptFloat
    from .label import ManuscriptLabel
    from .paragraph import ManuscriptParagraph
    from .reference import ManuscriptReference
    from .section import ManuscriptSection
    from .sentence import ManuscriptSentence
    from .statement import ManuscriptStatement


class ManuscriptFact(Fact):
    """Describe how one manuscript is put together, in the order a reader meets it."""

    root: str = Field(default="", description="file a build of this manuscript is pointed at")
    sections: list[ManuscriptSection] = Field(
        default=[], description="every heading, in reading order"
    )
    statements: list[ManuscriptStatement] = Field(
        default=[], description="every numbered statement environment, in reading order"
    )
    floats: list[ManuscriptFloat] = Field(
        default=[], description="every figure and table, in reading order"
    )
    labels: list[ManuscriptLabel] = Field(
        default=[], description="every cross reference target, in reading order"
    )
    references: list[ManuscriptReference] = Field(
        default=[], description="every cross reference, in reading order"
    )
    paragraphs: list[ManuscriptParagraph] = Field(
        default=[], description="every paragraph of running prose, in reading order"
    )
    sentences: list[ManuscriptSentence] = Field(
        default=[], description="every sentence of running prose, in reading order"
    )
