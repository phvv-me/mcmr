from typing import Annotated

from patos import FrozenModel
from pydantic import Field

from ...domain.primitives import NonEmptyStr

type Ratio = Annotated[float, Field(ge=0.0, le=1.0)]


class Evidence(FrozenModel):
    """Retain one provider claim supporting a named rule measurement."""

    signal: NonEmptyStr = Field(
        description="citation identifier unique within one fact's evidence"
    )
    detail: NonEmptyStr = Field(description="serialized content of the cited claim")
    source: NonEmptyStr = Field(description="repository relative path the claim was read from")
    confidence: Ratio = Field(
        default=1.0, description="provider certainty in the claim, from 0 to 1"
    )
