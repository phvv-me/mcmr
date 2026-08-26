from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptSection(ManuscriptPlace):
    """Retain one heading and how much prose it opens."""

    level: NonNegativeInt = Field(default=0, description="outline depth, zero being outermost")
    title: str = Field(default="", description="title as the heading states it")
    title_word_count: NonNegativeInt = Field(default=0, description="words in the title")
    label: str = Field(default="", description="cross reference target this heading declares")
    word_count: NonNegativeInt = Field(default=0, description="prose words this section holds")
    paragraph_count: NonNegativeInt = Field(default=0, description="paragraphs this section holds")
