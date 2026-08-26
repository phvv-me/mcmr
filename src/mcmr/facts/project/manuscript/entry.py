from pydantic import Field, PositiveInt

from .place import ManuscriptPlace


class ManuscriptEntry(ManuscriptPlace):
    """Retain one row of a manuscript's own notation index, per symbol it names."""

    symbol: str = Field(default="", description="symbol this row indexes")
    meaning: str = Field(default="", description="what the row says the symbol means")
    sense_count: PositiveInt = Field(
        default=1, description="senses the row separates, counted from its own wording"
    )
