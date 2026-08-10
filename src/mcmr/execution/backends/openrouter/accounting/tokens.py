import json
from functools import cached_property
from importlib import import_module
from typing import TYPE_CHECKING, cast

from patos import FrozenModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Protocol

    from pydantic import JsonValue


class RequestTokens(FrozenModel):
    """Bound request size with the model tokenizer when its vocabulary is known."""

    model: str

    if TYPE_CHECKING:

        class TokenEncoding(Protocol):
            ids: list[int]

        class ModelTokenizer(Protocol):
            def encode(self, sequence: str) -> RequestTokens.TokenEncoding: ...

        class TokenizerFactory(Protocol):
            @staticmethod
            def from_pretrained(identifier: str) -> RequestTokens.ModelTokenizer: ...

    @cached_property
    def tokenizer(self) -> ModelTokenizer | None:
        """Load the official tokenizer for models whose repository is unambiguous."""
        if self.model.startswith("deepseek/deepseek-v4-flash"):
            factory = cast(
                "type[RequestTokens.TokenizerFactory]",
                import_module("tokenizers").Tokenizer,
            )
            return factory.from_pretrained("deepseek-ai/DeepSeek-V4-Flash")
        return None

    def count(self, request: Mapping[str, JsonValue]) -> int:
        """Count a compact request or retain the strict serialized byte upper bound."""
        source = json.dumps(request, sort_keys=True, separators=(",", ":"))
        if self.tokenizer is None:
            return len(source.encode())
        return len(self.tokenizer.encode(source).ids)

    def estimate(self, request: Mapping[str, JsonValue]) -> int:
        """Estimate model tokens cheaply before exact final-pack verification."""
        serialized = json.dumps(request, sort_keys=True, separators=(",", ":"))
        return self.estimate_bytes(len(serialized.encode()))

    def estimate_bytes(self, serialized_bytes: int) -> int:
        """Turn a serialized-size projection into a model-aware token estimate."""
        if self.model.startswith("deepseek/deepseek-v4-flash"):
            return max(1, (serialized_bytes + 2) // 3)
        return serialized_bytes
