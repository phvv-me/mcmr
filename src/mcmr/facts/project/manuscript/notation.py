from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .entry import ManuscriptEntry
    from .site import ManuscriptSymbolSite
    from .symbol import ManuscriptSymbol
    from .term import ManuscriptTerm


class ManuscriptNotationFact(Fact):
    """Describe what one manuscript calls things, and where it says so."""

    root: str = Field(default="", description="file a build of this manuscript is pointed at")
    symbols: list[ManuscriptSymbol] = Field(
        default=[], description="every symbol the mathematics names"
    )
    sites: list[ManuscriptSymbolSite] = Field(
        default=[], description="every place the manuscript appears to introduce a symbol"
    )
    terms: list[ManuscriptTerm] = Field(
        default=[], description="every phrase the author marked as a name"
    )
    entries: list[ManuscriptEntry] = Field(
        default=[], description="every row of the manuscript's own notation index"
    )
