from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ....domain.policy import LengthDistribution, LengthDistributionValue
from ...foundation import NodeRef


class ProseSection(FrozenModel):
    """Retain normalized prose measurements after removing non-prose blocks."""

    text: str = Field(default="", description="docstring text this section normalizes")
    character_count: NonNegativeInt = Field(
        default=0, description="character count of the section's text"
    )
    token_count: NonNegativeInt = Field(
        default=0, description="whitespace separated word count of the section's text"
    )
    sentence_word_counts: LengthDistributionValue = Field(
        default=LengthDistribution(root=[]),
        description="word count of each sentence in the section",
    )
    paragraph_word_counts: LengthDistributionValue = Field(
        default=LengthDistribution(root=[]),
        description="word count of each paragraph in the section",
    )
    sentence_openers: list[str] = Field(
        default=[], description="lowercased first word of each sentence in the section"
    )
    node: NodeRef | None = Field(
        default=None, description="syntax node of the docstring this section was read from"
    )
