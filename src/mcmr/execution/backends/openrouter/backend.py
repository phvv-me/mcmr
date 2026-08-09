import asyncio
import json
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar, cast

from httpx import AsyncBaseTransport
from pydantic import Field, InstanceOf, JsonValue, PositiveInt

from ....domain import primitives
from ...queries import ModelQuery, answer_frame
from ...queries.contracts import ModelCandidate
from ...queries.runtime import ResolvedQuery
from ..batch import BatchProtocol
from ..batched import BatchedBackend
from ..repository import RepositoryProtocol
from .client import OpenRouterClient

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from enum import StrEnum

    from ....domain.contracts import ModelProvenance


class OpenRouterBackend(BatchedBackend):
    """Run each contextual rule through one schema-constrained OpenRouter completion."""

    name: ClassVar[str] = "openrouter"
    model: primitives.NonEmptyStr = "anthropic/claude-sonnet-5"
    reasoning_effort: primitives.NonEmptyStr = "none"
    timeout_seconds: int = Field(default=180, ge=1)
    prompt_token_budget: PositiveInt = 128_000
    max_output_tokens: PositiveInt | None = None
    transport: InstanceOf[AsyncBaseTransport] | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    @cached_property
    def client(self) -> OpenRouterClient:
        """Build the configured request client once."""
        return OpenRouterClient.model_validate(self, from_attributes=True)

    async def answered_many(
        self,
        queries: Sequence[ModelQuery[StrEnum]],
    ) -> Sequence[ResolvedQuery]:
        """Pack independent contextual rules, splitting only unsafe or unusable groups."""
        prepared: list[tuple[ModelQuery[StrEnum], list[dict[str, JsonValue]], BatchProtocol]] = []
        resolved: dict[int, ResolvedQuery] = {}
        for index, query in enumerate(queries):
            candidate_frame = query.candidates.collect()
            rows = cast("list[dict[str, JsonValue]]", candidate_frame.to_dicts())
            if not rows:
                resolved[index] = ResolvedQuery(
                    query=query.resolved(
                        candidate_frame,
                        answers=answer_frame(query, rows=[], outcomes=[]),
                    )
                )
                continue
            candidates = [ModelCandidate.from_row(row) for row in rows]
            prepared.append(
                (
                    query,
                    rows,
                    BatchProtocol(candidates=candidates, instructions=query.stated_instructions),
                )
            )
        packed = await self._packed(prepared)
        resolved.update(
            dict(
                zip(
                    [index for index in range(len(queries)) if index not in resolved],
                    packed,
                    strict=True,
                )
            )
        )
        return [resolved[index] for index in range(len(queries))]

    async def turn(
        self,
        schema: Mapping[str, JsonValue],
        *,
        prompt: str,
        name: str,
    ) -> tuple[str, ModelProvenance]:
        """Run one bounded HTTP completion for this schema-constrained prompt."""
        return await self.client.invoke(schema, prompt=prompt, name=name)

    async def _packed(
        self,
        prepared: Sequence[tuple[ModelQuery[StrEnum], list[dict[str, JsonValue]], BatchProtocol]],
    ) -> list[ResolvedQuery]:
        """Answer one safe packed group or bisect it around transport and validation failures."""
        if not prepared:
            return []
        queries = [item[0] for item in prepared]
        protocol = RepositoryProtocol(batches=[item[2] for item in prepared])
        prompt = protocol.prompt(queries)
        schema = protocol.output_schema(queries)
        if not self._within_budget(schema, prompt):
            return await self._split(prepared)
        try:
            source, provenance = await self.turn(schema, prompt=prompt, name="repository_rules")
        except OSError, RuntimeError, ValueError:
            return await self._split(prepared)
        try:
            outcomes = protocol.outcomes(source, queries, provenance)
        except ValueError:
            return await self._split(prepared)
        return [
            ResolvedQuery(
                query=query.resolved(
                    query.candidates.collect(),
                    answers=answer_frame(query, rows=rows, outcomes=answers),
                ),
                spend=self.spend(rows, answers),
            )
            for (query, rows, _), answers in zip(prepared, outcomes, strict=True)
        ]

    async def _split(
        self,
        prepared: Sequence[tuple[ModelQuery[StrEnum], list[dict[str, JsonValue]], BatchProtocol]],
    ) -> list[ResolvedQuery]:
        """Bisect a packed group and retain the legacy isolated backend as the final fallback."""
        if len(prepared) == 1:
            return [await self.answered(prepared[0][0])]
        middle = len(prepared) // 2
        left, right = await asyncio.gather(
            self._packed(prepared[:middle]),
            self._packed(prepared[middle:]),
        )
        return [*left, *right]

    def _within_budget(self, schema: Mapping[str, JsonValue], prompt: str) -> bool:
        """Bound a packed request conservatively without requiring a model tokenizer."""
        request = self.client.body(schema, prompt=prompt, name="repository_rules")
        serialized = json.dumps(request, sort_keys=True, separators=(",", ":"))
        # JSON escaping makes this ASCII. Its byte length is therefore a strict token-count upper
        # bound, including the schema and request wrappers, even without a model tokenizer.
        return len(serialized.encode()) <= self.prompt_token_budget


OpenRouterBackend.model_rebuild(_types_namespace={"primitives": primitives})
