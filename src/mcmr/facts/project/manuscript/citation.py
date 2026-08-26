from pydantic import Field

from .place import ManuscriptPlace


class ManuscriptCitation(ManuscriptPlace):
    """Retain one bibliography reference and the locator it pins its source to."""

    key: str = Field(default="", description="bibliography key this citation names")
    pin: str = Field(
        default="", description="page, section, or equation the citation pins, empty when unpinned"
    )
