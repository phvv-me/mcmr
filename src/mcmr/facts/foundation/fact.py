from typing import Annotated, ClassVar

from annotated_types import Predicate
from patos import FrozenModel
from pydantic import Field

from .evidence import Evidence
from .span import SourceSpan


class Fact(FrozenModel):
    """Identify one independently invalidated unit supplied to rules."""

    external_evidence: ClassVar[bool] = False
    key: str = Field(description="identifier unique to this fact within its family")
    span: SourceSpan = Field(description="source range this fact was extracted from")
    language: str | None = Field(
        default=None, description="source language the fact was extracted from, empty when none"
    )
    evidence: Annotated[
        list[Evidence],
        Predicate(lambda claims: len(claims) == len({claim.signal for claim in claims})),
    ] = Field(default=[], description="provider claims backing this fact, unique per signal")
