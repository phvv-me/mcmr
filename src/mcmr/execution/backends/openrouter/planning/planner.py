from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ....queries.contracts import ModelMode
from .pack import RepositoryPack

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic import JsonValue, PositiveInt

    from ..accounting import RequestTokens
    from ..client import OpenRouterClient
    from .rule import RepositoryRule


class RepositoryPlanner:
    """Partition a repository evidence graph under provider input and output limits."""

    def __init__(
        self,
        *,
        client: OpenRouterClient,
        counter: RequestTokens,
        candidate_budget: PositiveInt,
        prompt_token_budget: PositiveInt,
        output_token_budget: PositiveInt | None,
    ) -> None:
        self.client = client
        self.counter = counter
        self.candidate_budget = candidate_budget
        self.prompt_token_budget = prompt_token_budget
        self.output_token_budget = output_token_budget
        self.measured_input_tokens: dict[str, int] = {}
        self.estimated_input_tokens: dict[str, int] = {}

    @property
    def maximum_output_tokens(self) -> int:
        """Return the configured response ceiling or an effectively unbounded fallback."""
        return self.output_token_budget or 2**31 - 1

    @property
    def reasoning_tokens(self) -> int:
        """Reserve OpenRouter's documented effort share before the visible JSON answer."""
        if self.output_token_budget is None or self.client.reasoning_effort == "none":
            return 0
        ratios = {
            "minimal": 0.1,
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "xhigh": 0.95,
            "max": 0.95,
        }
        ratio = ratios.get(self.client.reasoning_effort, 0.5)
        return min(32_000, max(1024, int(self.output_token_budget * ratio)))

    def output_tokens(self, pack: RepositoryPack) -> int | None:
        """Bound one request without starving smaller isolation retries."""
        if self.output_token_budget is None:
            return None
        floor = min(32_000, self.output_token_budget)
        return min(self.output_token_budget, max(floor, self._required_output_tokens(pack)))

    def plan(self, rules: Sequence[RepositoryRule]) -> list[RepositoryPack]:
        """Build dependency components, bound them, then fill available request capacity."""
        units = [
            unit
            for component in self._components(rules)
            for unit in self._bounded(RepositoryPack.of(component), depth=2)
        ]
        provisional = self._packed(units, exact=False)
        verified = [unit for pack in provisional for unit in self._bounded_exact(pack, depth=2)]
        return self._packed(verified, exact=True)

    def safely_plan(self, rules: Sequence[RepositoryRule]) -> list[RepositoryPack] | None:
        """Return no grouped plan when one candidate needs the legacy protocol."""
        try:
            return self.plan(rules)
        except ValueError:
            return None

    def split(self, pack: RepositoryPack) -> tuple[RepositoryPack, RepositoryPack]:
        """Bisect candidates while keeping every original position exactly once."""
        left: list[RepositoryRule] = []
        right: list[RepositoryRule] = []
        singles: list[RepositoryRule] = []
        for rule in pack.rules:
            size = len(rule.batch.candidates)
            if size == 1:
                singles.append(rule)
                continue
            middle = size // 2
            left.append(rule.selected(list(range(middle))))
            right.append(rule.selected(list(range(middle, size))))
        for position, rule in enumerate(singles):
            (left if position % 2 == 0 else right).append(rule)
        return RepositoryPack.of(left), RepositoryPack.of(right)

    def _areas(self, pack: RepositoryPack, *, depth: int) -> list[RepositoryPack]:
        """Partition candidate slices by stable repository directory ownership."""
        grouped: dict[str, list[RepositoryRule]] = {}
        for rule in pack.rules:
            selected: dict[str, list[int]] = {}
            for position, candidate in enumerate(rule.batch.candidates):
                parts = PurePosixPath(candidate.path).parts
                area = "/".join(parts[:depth]) if len(parts) >= depth else candidate.path
                selected.setdefault(area, []).append(position)
            for area, positions in selected.items():
                grouped.setdefault(area, []).append(rule.selected(positions))
        return [RepositoryPack.of(rules) for rules in grouped.values()]

    def _bounded(self, pack: RepositoryPack, *, depth: int) -> list[RepositoryPack]:
        """Split an estimated overrun by repository ownership then cardinality."""
        if self._fits(pack):
            return [pack]
        areas = self._areas(pack, depth=depth)
        if len(areas) > 1:
            return [unit for area in areas for unit in self._bounded(area, depth=depth + 1)]
        left, right = self.split(pack)
        if right.rules:
            return [
                *self._bounded(left, depth=depth + 1),
                *self._bounded(right, depth=depth + 1),
            ]
        raise ValueError("One contextual candidate exceeds the configured prompt budget")

    def _bounded_exact(self, pack: RepositoryPack, *, depth: int) -> list[RepositoryPack]:
        """Verify final packs with the model tokenizer and split exact overruns."""
        if self._fits_exact(pack):
            return [pack]
        areas = self._areas(pack, depth=depth)
        if len(areas) > 1:
            return [unit for area in areas for unit in self._bounded_exact(area, depth=depth + 1)]
        left, right = self.split(pack)
        if right.rules:
            return [
                *self._bounded_exact(left, depth=depth + 1),
                *self._bounded_exact(right, depth=depth + 1),
            ]
        raise ValueError("One contextual candidate exceeds the configured prompt budget")

    def _components(self, rules: Sequence[RepositoryRule]) -> list[list[RepositoryRule]]:
        """Find transitive rule groups that read identical evidence claims."""
        neighbors = self._neighbors(rules)
        pending = list(rules)
        components: list[list[RepositoryRule]] = []
        while pending:
            connected = {pending[0].index}
            frontier = set(connected)
            while frontier:
                frontier = set().union(*(neighbors[index] for index in frontier)) - connected
                connected.update(frontier)
            components.append([rule for rule in pending if rule.index in connected])
            pending = [rule for rule in pending if rule.index not in connected]
        return components

    def _estimate_input_tokens(self, pack: RepositoryPack) -> int:
        """Measure one fast planning estimate and reuse identical candidate slices."""
        identity = self._identity(pack)
        if measured := self.estimated_input_tokens.get(identity):
            return measured
        evidence: set[tuple[str, str, str, float]] = set()
        serialized_bytes = 4096
        for rule in pack.rules:
            serialized_bytes += len(rule.query.stated_instructions.encode())
            rubric = (
                rule.query.category
                if rule.query.mode is ModelMode.CLASSIFY
                else rule.query.criteria
            )
            serialized_bytes += sum(len(str(item).encode()) for item in rubric)
            for candidate in rule.batch.candidates:
                serialized_bytes += 16 + 6 * len(candidate.retained)
                evidence.update(
                    (identifier, claim.detail, claim.source, claim.confidence)
                    for identifier, claim in candidate.retained.items()
                )
        serialized_bytes += sum(
            len(identifier.encode()) + len(detail.encode()) + len(source.encode()) + 24
            for identifier, detail, source, _ in evidence
        )
        measured = self.counter.estimate_bytes(serialized_bytes)
        self.estimated_input_tokens[identity] = measured
        return measured

    def _fits(self, pack: RepositoryPack) -> bool:
        """Use a cheap estimate while shaping candidate packs."""
        return (
            pack.answer_rows <= self.candidate_budget
            and self._estimate_input_tokens(pack) <= self.prompt_token_budget
            and self._required_output_tokens(pack) <= self.maximum_output_tokens
        )

    def _fits_exact(self, pack: RepositoryPack) -> bool:
        """Require the tokenized request and expected response to fit."""
        return (
            pack.answer_rows <= self.candidate_budget
            and self._input_tokens(pack) <= self.prompt_token_budget
            and self._required_output_tokens(pack) <= self.maximum_output_tokens
        )

    def _identity(self, pack: RepositoryPack) -> str:
        """Name one exact collection of original rule and candidate positions."""
        return repr([[rule.index, rule.positions] for rule in pack.rules])

    def _input_tokens(self, pack: RepositoryPack) -> int:
        """Count the exact schema-constrained request this pack would send."""
        identity = self._identity(pack)
        if measured := self.measured_input_tokens.get(identity):
            return measured
        measured = self.counter.count(self._request(pack))
        self.measured_input_tokens[identity] = measured
        return measured

    def _neighbors(self, rules: Sequence[RepositoryRule]) -> dict[int, set[int]]:
        """Connect every rule index that reads one shared evidence identity."""
        owners: dict[str, set[int]] = {}
        for rule in rules:
            for identifier in rule.evidence:
                owners.setdefault(identifier, set()).add(rule.index)
        neighbors = {rule.index: {rule.index} for rule in rules}
        for connected in owners.values():
            for owner in connected:
                neighbors[owner].update(connected)
        return neighbors

    def _packed(
        self,
        units: Sequence[RepositoryPack],
        *,
        exact: bool,
    ) -> list[RepositoryPack]:
        """Best-fit units into bounded requests using estimated or exact counts."""
        measure = self._input_tokens if exact else self._estimate_input_tokens
        fits = self._fits_exact if exact else self._fits
        measured = sorted(
            ((measure(unit), unit) for unit in units), reverse=True, key=lambda x: x[0]
        )
        bins: list[tuple[int, RepositoryPack]] = []
        reserve = min(4096, self.prompt_token_budget // 20)
        for tokens, unit in measured:
            destination = next(
                (
                    index
                    for index, (used, packed) in enumerate(bins)
                    if used + tokens <= self.prompt_token_budget - reserve
                    and fits(RepositoryPack.of([*packed.rules, *unit.rules]))
                ),
                None,
            )
            if destination is None:
                bins.append((tokens, unit))
                continue
            _, packed = bins[destination]
            combined = RepositoryPack.of([*packed.rules, *unit.rules])
            bins[destination] = (measure(combined), combined)
        return [pack for _, pack in bins]

    def _request(self, pack: RepositoryPack) -> dict[str, JsonValue]:
        """Build the schema-constrained request both planning counters inspect."""
        protocol = pack.protocol
        return self.client.body(
            protocol.output_schema(pack.queries),
            cache_key=protocol.cache_key(pack.queries),
            prompt=protocol.prompt(pack.queries),
            name="repository_rules",
        )

    def _required_output_tokens(self, pack: RepositoryPack) -> int:
        """Reserve compact cited answers plus bounded model reasoning."""
        return self.reasoning_tokens + 2048 + pack.answer_rows * 96 + pack.answer_units * 8
