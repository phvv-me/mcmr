from functools import cached_property
from typing import Annotated

from patos import FrozenModel
from pydantic import Field, NonNegativeFloat

from ..provenance import ProvenanceTotals
from .result import ContextualSweepResult


class ContextualSweepReport(FrozenModel):
    """Summarize one live pass through every contextual rule contract."""

    results: Annotated[list[ContextualSweepResult], Field(min_length=1)]
    elapsed_seconds: NonNegativeFloat

    @property
    def cached_input_tokens(self) -> int:
        """Return cached input tokens reported once per isolated rule turn."""
        return self._tokens.cached_input_tokens

    @property
    def error_count(self) -> int:
        """Return isolated backend turns that failed their output contract."""
        return sum(bool(item.error) for item in self.results)

    @property
    def input_tokens(self) -> int:
        """Return input tokens reported once per isolated rule turn."""
        return self._tokens.input_tokens

    @property
    def message_characters(self) -> int:
        """Return retained explanation characters across every contextual rule."""
        return sum(len(message) for item in self.results for message in item.messages)

    @property
    def output_tokens(self) -> int:
        """Return output tokens reported once per isolated rule turn."""
        return self._tokens.output_tokens

    @property
    def reasoning_tokens(self) -> int:
        """Return reasoning tokens reported once per isolated rule turn."""
        return self._tokens.reasoning_tokens

    @cached_property
    def _tokens(self) -> ProvenanceTotals:
        """Total every token counter across every isolated rule turn."""
        return ProvenanceTotals.of(item.provenance for item in self.results)
