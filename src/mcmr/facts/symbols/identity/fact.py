from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from ..typing.scope import TypingScope
    from .symbol import Symbol


class SymbolFact(Fact):
    """Describe one resolved symbol declaration and its uses."""

    symbols: list[Symbol] = Field(
        default=[], description="names this file binds, scoped by where each is bound"
    )
    typing_scopes: list[TypingScope] = Field(
        default=[], description="cohesive directories of typing declarations and their reuse"
    )
