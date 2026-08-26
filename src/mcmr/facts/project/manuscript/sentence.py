from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptSentence(ManuscriptPlace):
    """Retain one sentence of running prose."""

    index: NonNegativeInt = Field(
        default=0, description="position of the sentence in its paragraph"
    )
    word_count: NonNegativeInt = Field(default=0, description="words the sentence holds")
    text: str = Field(default="", description="sentence as the paragraph states it")
