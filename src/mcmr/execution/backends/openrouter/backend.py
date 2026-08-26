import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar, cast

from httpx2 import AsyncBaseTransport
from pydantic import Field, InstanceOf, JsonValue, PositiveInt

from ....domain import primitives
from ....domain.contracts import ModelSpend
from ...queries import ModelQuery, answer_frame
from ...queries.contracts import Assessment, Classification, ModelCandidate, ModelMode
from ...queries.runtime import ResolvedQuery
from ..batch import BatchProtocol
from ..batched import BatchedBackend
from .accounting import RequestTokens
from .answer import RepositoryAnswer
from .client import OpenRouterClient
from .planning import RepositoryPack, RepositoryPlanner, RepositoryRule
from .transport import RepositoryProgress, StreamObserver

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from enum import StrEnum

    from ....domain.contracts import ModelProvenance


class OpenRouterBackend(BatchedBackend):
    """Run contextual evidence packs through schema-constrained OpenRouter responses."""

    name: ClassVar[str] = "openrouter"
    model: primitives.NonEmptyStr = "anthropic/claude-sonnet-5"
    reasoning_effort: primitives.NonEmptyStr = "none"
    candidate_budget: PositiveInt = 512
    prompt_token_budget: PositiveInt = 128_000
    max_output_tokens: PositiveInt | None = None
    contract_attempts: PositiveInt = 2
    transport: InstanceOf[AsyncBaseTransport] | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    @cached_property
    def client(self) -> OpenRouterClient:
        """Build the configured request client once."""
        return OpenRouterClient.model_validate(self, from_attributes=True)

    @cached_property
    def planner(self) -> RepositoryPlanner:
        """Build the dependency-aware evidence pack planner once."""
        return RepositoryPlanner(
            client=self.client,
            counter=self.request_tokens,
            candidate_budget=self.candidate_budget,
            prompt_token_budget=self.prompt_token_budget,
            output_token_budget=self.max_output_tokens,
        )

    @cached_property
    def request_tokens(self) -> RequestTokens:
        """Build the model-aware request counter once."""
        return RequestTokens(model=self.model)

    async def answered_many(
        self,
        queries: Sequence[ModelQuery[StrEnum]],
    ) -> Sequence[ResolvedQuery]:
        """Answer normalized packs and restore every query's original candidate order."""
        prepared, resolved = self._prepared(queries)
        answered = await self._planned(prepared)
        by_rule: dict[int, list[tuple[int, Classification[StrEnum] | Assessment]]] = {}
        paid: dict[int, dict[str, list[ModelSpend]]] = {}
        for answer in answered:
            by_rule.setdefault(answer.rule.index, []).extend(
                zip(answer.rule.positions, answer.outcomes, strict=True)
            )
            for path, spend in self.spend(answer.rule.rows, answer.outcomes).items():
                paid.setdefault(answer.rule.index, {}).setdefault(path, []).append(spend)
        for rule in prepared:
            ordered = sorted(by_rule[rule.index], key=lambda item: item[0])
            if [position for position, _ in ordered] != list(range(len(rule.rows))):
                raise ValueError("Repository planning lost or duplicated rule candidates")
            outcomes = [self._trusted(rule.query, outcome) for _, outcome in ordered]
            resolved[rule.index] = ResolvedQuery(
                query=rule.query.resolved(
                    rule.query.candidates.collect(),
                    answers=answer_frame(rule.query, rows=rule.rows, outcomes=outcomes),
                ),
                spend={
                    path: ModelSpend.of(parts) for path, parts in paid.get(rule.index, {}).items()
                },
            )
        return [resolved[index] for index in range(len(queries))]

    async def turn(
        self,
        schema: Mapping[str, JsonValue],
        *,
        prompt: str,
        name: str,
    ) -> tuple[str, ModelProvenance]:
        """Run one bounded HTTP completion for an isolated legacy protocol."""
        return await self.client.invoke(schema, prompt=prompt, name=name)

    async def _answer_pack(
        self,
        pack: RepositoryPack,
        observer: StreamObserver | None = None,
    ) -> list[RepositoryAnswer]:
        """Answer one planned pack with one bounded repair attempt for contract drift."""
        protocol = pack.protocol
        cache_key = protocol.cache_key(pack.queries)
        attempt = 0
        async with self.limiter:
            while True:
                attempt_cache_key = (
                    cache_key if attempt == 0 else f"{cache_key}-contract-{attempt}"
                )
                source, provenance = await self.client.invoke(
                    protocol.output_schema(pack.queries),
                    cache_key=attempt_cache_key,
                    max_output_tokens=self.planner.output_tokens(pack),
                    prompt=protocol.prompt(pack.queries),
                    name="repository_rules",
                    observer=observer,
                )
                try:
                    outcomes = protocol.outcomes(source, pack.queries, provenance)
                except ValueError as error:
                    if attempt + 1 == self.contract_attempts:
                        raise self._contract_error(source, error) from error
                    attempt += 1
                    continue
                return [
                    RepositoryAnswer(rule=rule, outcomes=list(answers))
                    for rule, answers in zip(pack.rules, outcomes, strict=True)
                ]

    def _contract_error(self, source: str, error: ValueError) -> ValueError:
        """Describe one malformed grouped answer without repeating its full content."""
        preview = source.strip().replace("\n", " ")[:300]
        return ValueError(
            f"OpenRouter violated the repository answer contract. {error}. "
            f"Response began with {preview!r} from {type(self).__name__}"
        )

    async def _legacy(self, rule: RepositoryRule) -> RepositoryAnswer:
        """Use established bounded candidate batches for one irreducible rule slice."""
        outcomes: Sequence[Classification[StrEnum] | Assessment]
        if rule.query.mode is ModelMode.CLASSIFY:
            outcomes = await self.classify_many(
                rule.batch.candidates,
                category=rule.query.category,
                instructions=rule.query.stated_instructions,
            )
        else:
            outcomes = await self.assess_many(
                rule.batch.candidates,
                criteria=rule.query.criteria,
                instructions=rule.query.stated_instructions,
            )
        return RepositoryAnswer(rule=rule, outcomes=list(outcomes))

    async def _planned(self, rules: Sequence[RepositoryRule]) -> list[RepositoryAnswer]:
        """Plan every nonempty rule or retain legacy batches for an irreducible candidate."""
        if not rules:
            return []
        packs = self.planner.safely_plan(rules)
        if packs is None:
            return list(await asyncio.gather(*(self._legacy(rule) for rule in rules)))
        first, *remaining = packs
        with RepositoryProgress(len(packs)) as progress:
            answered = await self._answer_pack(first, progress.observer(0))
            grouped = await asyncio.gather(
                *(
                    self._answer_pack(pack, progress.observer(index))
                    for index, pack in enumerate(remaining, start=1)
                )
            )
        return [*answered, *(answer for group in grouped for answer in group)]

    def _prepared(
        self,
        queries: Sequence[ModelQuery[StrEnum]],
    ) -> tuple[list[RepositoryRule], dict[int, ResolvedQuery]]:
        """Collect candidates once and resolve empty relations locally."""
        prepared: list[RepositoryRule] = []
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
            prepared.append(
                RepositoryRule(
                    index=index,
                    query=query,
                    rows=rows,
                    positions=list(range(len(rows))),
                    batch=BatchProtocol(
                        candidates=[ModelCandidate.from_row(row) for row in rows],
                        instructions=query.stated_instructions,
                    ),
                )
            )
        return prepared, resolved


OpenRouterBackend.model_rebuild(_types_namespace={"primitives": primitives})
