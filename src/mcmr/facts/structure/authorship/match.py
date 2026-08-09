from typing import TYPE_CHECKING

from pydantic import Field

from .groups import AuthorshipFields

if TYPE_CHECKING:
    from pydantic import NonNegativeFloat

    from ....domain.primitives import NonEmptyStr
    from ...foundation import SourceSpan


class AuthorshipMatch(AuthorshipFields):
    """Retain one external analyzer match without inferring authorship."""

    matched_text: NonEmptyStr = Field(description="exact text span the analyzer flagged")
    span: SourceSpan = Field(description="source location of the matched text")
    relative_likelihood: NonNegativeFloat | None = Field(
        default=None,
        description="provider-reported relative likelihood of the match, when reported",
    )
    is_eligible: bool = Field(
        default=True, description="whether the match counts toward eligible measurement"
    )
