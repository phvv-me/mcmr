from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptParagraph(ManuscriptPlace):
    """Retain one paragraph of running prose and its shape."""

    word_count: NonNegativeInt = Field(default=0, description="words the paragraph holds")
    sentence_count: NonNegativeInt = Field(default=0, description="sentences the paragraph holds")
    in_cells: bool = Field(default=False, description="whether the prose sits inside table cells")
    in_float: bool = Field(default=False, description="whether the prose sits inside a float")
