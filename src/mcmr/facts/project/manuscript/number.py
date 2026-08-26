from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptNumber(ManuscriptPlace):
    """Retain one number exactly as the manuscript printed it."""

    literal: str = Field(default="", description="number as written, with its own precision")
    in_cells: bool = Field(default=False, description="whether the number sits in a table cell")
    float_label: str = Field(
        default="", description="label of the float holding the number, empty in running prose"
    )
    names_ratio: bool = Field(
        default=False, description="whether the sentence names a derived quantity"
    )
    sentence_number_count: NonNegativeInt = Field(
        default=0, description="numbers the same sentence states"
    )
