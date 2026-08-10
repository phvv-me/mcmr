import json
from functools import cached_property
from typing import TYPE_CHECKING

from huggingface_hub import hf_hub_download
from patos import FrozenModel

from .....kernel_tables import HuggingFaceTokenizer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import JsonValue


class RequestTokens(FrozenModel):
    """Bound request size with the model tokenizer when its vocabulary is known."""

    model: str

    @cached_property
    def tokenizer(self) -> HuggingFaceTokenizer | None:
        """Load the official tokenizer for models whose repository is unambiguous."""
        if self.model.startswith("deepseek/deepseek-v4-flash"):
            return HuggingFaceTokenizer(
                hf_hub_download(
                    repo_id="deepseek-ai/DeepSeek-V4-Flash",
                    filename="tokenizer.json",
                )
            )
        return None

    def count(self, request: Mapping[str, JsonValue]) -> int:
        """Count a compact request or retain the strict serialized byte upper bound."""
        source = json.dumps(request, sort_keys=True, separators=(",", ":"))
        if self.tokenizer is None:
            return len(source.encode())
        return self.tokenizer.count(source)

    def estimate(self, request: Mapping[str, JsonValue]) -> int:
        """Estimate model tokens cheaply before exact final-pack verification."""
        serialized = json.dumps(request, sort_keys=True, separators=(",", ":"))
        return self.estimate_bytes(len(serialized.encode()))

    def estimate_bytes(self, serialized_bytes: int) -> int:
        """Turn a serialized-size projection into a model-aware token estimate."""
        if self.model.startswith("deepseek/deepseek-v4-flash"):
            return max(1, (serialized_bytes + 2) // 3)
        return serialized_bytes
