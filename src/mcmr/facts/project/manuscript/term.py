from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptTerm(ManuscriptPlace):
    """Retain one phrase the author marked, which is how a term is usually introduced."""

    term: str = Field(default="", description="marked phrase, lowered and stripped")
    command: str = Field(default="", description="command that marked the phrase")
    mark_order: NonNegativeInt = Field(
        default=0, description="reading order at which the phrase is marked"
    )
    use_count: NonNegativeInt = Field(
        default=0, description="times the phrase appears anywhere in the body prose"
    )
    first_use_order: NonNegativeInt = Field(
        default=0, description="reading order at which the phrase is first used"
    )
