from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .mechanism import InteropMechanism
    from .reference import InteropReference


class InteropFact(Fact):
    """Describe an artifact declared in one language and reached from another."""

    name: str = Field(description="name of the cross-language artifact")
    mechanism: InteropMechanism = Field(description="mechanism the artifact is reached through")
    declared_language: str = Field(description="language the artifact is declared in")
    references: list[InteropReference] = Field(
        default=[], description="places that reach the artifact from another language"
    )
