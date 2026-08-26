from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptSymbol(ManuscriptPlace):
    """Retain one mathematical symbol and where the reader first met it."""

    name: str = Field(default="", description="symbol spelled the way the reader meets it")
    use_count: NonNegativeInt = Field(default=0, description="math spans this symbol appears in")
    section_count: NonNegativeInt = Field(
        default=0, description="distinct sections this symbol appears in"
    )
    first_order: NonNegativeInt = Field(
        default=0, description="reading order at which the symbol is first met"
    )
    last_section: NonNegativeInt = Field(
        default=0, description="section the last counted occurrence sat in"
    )
