from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptFloat(ManuscriptPlace):
    """Retain one figure or table and the caption it carries."""

    kind: str = Field(default="", description="whether the float is a figure or a table")
    label: str = Field(default="", description="cross reference target this float declares")
    caption: str = Field(default="", description="caption text as the float states it")
    caption_word_count: NonNegativeInt = Field(default=0, description="words in the caption")
