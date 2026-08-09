from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr


class AuthorshipFields(FrozenModel):
    """Retain analyzer segment, provider, version, and rule."""

    segment: NonEmptyStr = Field(
        description="identifier of the text segment the match was drawn from"
    )
    provider: NonEmptyStr = Field(
        description="name of the external analyzer that reported the match"
    )
    provider_version: str = Field(
        default="", description="version of the analyzer, empty when not reported"
    )
    rule: str = Field(default="", description="analyzer-specific rule or check name that fired")
