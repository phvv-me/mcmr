from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptSymbolSite(ManuscriptPlace):
    """Retain one place a manuscript appears to introduce a symbol."""

    symbol: str = Field(default="", description="symbol this site introduces")
    statement_number: NonNegativeInt = Field(
        default=0,
        description="statement holding the site counted from one, zero when it sits in none",
    )
    is_display: bool = Field(
        default=False, description="whether the introduction was set as a display"
    )
