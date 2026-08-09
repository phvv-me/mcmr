from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import NonNegativeInt

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Protocol

    class TokenUsage(Protocol):
        """Expose what one model turn or one earlier spend states about what it cost."""

        @property
        def backend(self) -> str: ...

        @property
        def model(self) -> str: ...

        @property
        def reasoning_effort(self) -> str: ...

        @property
        def input_tokens(self) -> int: ...

        @property
        def cached_input_tokens(self) -> int: ...

        @property
        def output_tokens(self) -> int: ...


class ModelSpend(FrozenModel):
    """State what the model turns behind one contextual answer cost.

    A contextual rule is the only kind of rule that costs money to run, and the amount is what
    tells an expensive rule apart from a cheap one that fires just as often. The identity of the
    backend travels with the counts because the same rule costs a different amount under a
    different model, so a number without the model that produced it compares nothing.
    """

    backend: str = ""
    model: str = ""
    reasoning_effort: str = ""
    input_tokens: NonNegativeInt = 0
    cached_input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0

    @property
    def properties(self) -> dict[str, str]:
        """Return the flat key and value pairs a receiving system stores beside a verdict.

        A spend nobody paid names no backend, and a deterministic rule is exactly that, so it
        states nothing rather than a row of zeroes a reader has to learn to ignore. The cached
        input travels beside the fresh input because a harness that reuses a prompt reports
        almost all of its input as cached, and a rule read as costing one token would be a lie.
        """
        if not self.backend:
            return {}
        stated = {
            "backend": self.backend,
            "model": self.model,
            "reasoningEffort": self.reasoning_effort,
            "inputTokens": str(self.input_tokens),
            "cachedInputTokens": str(self.cached_input_tokens),
            "outputTokens": str(self.output_tokens),
        }
        return {name: value for name, value in stated.items() if value}

    @property
    def tokens(self) -> int:
        """Return every token this spend paid for, which is the one number a cost sorts by."""
        return self.input_tokens + self.cached_input_tokens + self.output_tokens

    @classmethod
    def of(cls, counted: Iterable[TokenUsage]) -> ModelSpend:
        """Return what several distinct model turns or earlier spends cost together.

        One rule asks one backend, so the first part that names one names the whole sum, and a
        part left unnamed by a deterministic rule adds its nothing without erasing that name.
        """
        parts = list(counted)
        named = next((part for part in parts if part.backend), None)
        return cls(
            backend="" if named is None else named.backend,
            model="" if named is None else named.model,
            reasoning_effort="" if named is None else named.reasoning_effort,
            input_tokens=sum(part.input_tokens for part in parts),
            cached_input_tokens=sum(part.cached_input_tokens for part in parts),
            output_tokens=sum(part.output_tokens for part in parts),
        )
