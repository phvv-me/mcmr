from patos import FrozenModel
from pydantic import Field, NonNegativeInt, PositiveInt


class CommentGroupFields(FrozenModel):
    """Retain comment text, neighbors, documentation role, and measured sizes."""

    text: str = Field(default="", description="comment body text with its markers stripped")
    preceding_source: str = Field(
        default="", description="up to three source lines immediately before the comment group"
    )
    following_source: str = Field(
        default="", description="up to three source lines immediately after the comment group"
    )
    is_documentation: bool = Field(
        default=False, description="whether the comment uses a documentation marker"
    )
    line_count: PositiveInt = Field(description="number of source lines the comment group spans")
    character_count: NonNegativeInt = Field(
        description="number of characters the raw comment text holds"
    )
    token_count: NonNegativeInt = Field(
        description="number of whitespace separated tokens the raw comment text holds"
    )
