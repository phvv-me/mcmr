from types import SimpleNamespace
from typing import TYPE_CHECKING

import polars as pl
import pytest

from mcmr.execution import ModelCandidate, backends
from mcmr.execution.backends import openrouter
from mcmr.execution.queries import ModelMode, ModelQuery
from mcmr.facts import Evidence

from ...backend_values import criteria
from ...fakes import Category

if TYPE_CHECKING:
    from pydantic import JsonValue


def query(*, mode: ModelMode = ModelMode.CLASSIFY) -> ModelQuery[Category]:
    """Build one controlled query without coupling planner tests to a fact table."""
    if mode is ModelMode.CLASSIFY:
        return ModelQuery(
            candidates=pl.LazyFrame(),
            category=Category,
            instructions="Judge retained structure.",
            mode=mode,
        )
    return ModelQuery(
        candidates=pl.LazyFrame(),
        category=Category,
        instructions="Assess retained structure.",
        mode=mode,
        criteria=list(criteria()),
        decision_table=[],
        default=Category.UNCERTAIN,
        uncertain=Category.UNCERTAIN,
    )


def rule(
    index: int,
    candidates: list[ModelCandidate],
    *,
    mode: ModelMode = ModelMode.CLASSIFY,
) -> openrouter.RepositoryRule:
    """Bind controlled candidates to their stable repository positions."""
    return openrouter.RepositoryRule(
        index=index,
        query=query(mode=mode),
        rows=[{"path": item.path} for item in candidates],
        positions=list(range(len(candidates))),
        batch=backends.BatchProtocol(
            candidates=candidates,
            instructions="Judge retained structure.",
        ),
    )


def claim(path: str, evidence: Evidence) -> ModelCandidate:
    """Build one path-owned candidate with a selected dependency identity."""
    return ModelCandidate(
        fact_id=f"fact:{path}",
        path=path,
        subject={"fields": {"signal": evidence.signal}, "records": [], "values": []},
        evidence=[evidence.model_copy(update={"source": path})],
    )


def planner(
    *,
    candidate_budget: int = 512,
    prompt_budget: int = 1_000_000,
    output_budget: int | None = None,
    counter: openrouter.RequestTokens | None = None,
    effort: str = "none",
) -> openrouter.RepositoryPlanner:
    """Build a deterministic byte-counted planner without a network tokenizer."""
    client = openrouter.OpenRouterClient(model="vendor/model", reasoning_effort=effort)
    return openrouter.RepositoryPlanner(
        client=client,
        counter=counter or openrouter.RequestTokens(model=client.model),
        candidate_budget=candidate_budget,
        prompt_token_budget=prompt_budget,
        output_token_budget=output_budget,
    )


def request_tokens(
    current: openrouter.RepositoryPlanner,
    pack: openrouter.RepositoryPack,
) -> int:
    """Count one pack through the same public transport and protocol contracts."""
    protocol = pack.protocol
    request = current.client.body(
        protocol.output_schema(pack.queries),
        cache_key=protocol.cache_key(pack.queries),
        prompt=protocol.prompt(pack.queries),
        name="repository_rules",
    )
    return current.counter.count(request)


class OptimisticCounter(openrouter.RequestTokens):
    """Force final verification to catch what the fast estimate misses."""

    def estimate_bytes(self, serialized_bytes: int) -> int:
        return 1


def test_repository_rule_slices_recombine_in_original_order() -> None:
    """Candidate splitting remains lossless even when slices arrive out of order."""
    original = rule(
        0,
        [
            claim("src/a.py", Evidence(signal="first", detail="fact", source="ignored")),
            claim("src/b.py", Evidence(signal="second", detail="fact", source="ignored")),
        ],
    )
    combined = openrouter.RepositoryPack.of([original.selected([1]), original.selected([0])])

    assert (
        combined.rules[0].positions,
        combined.answer_units,
        combined.queries,
        len(combined.protocol.batches[0].candidates),
    ) == ([0, 1], 2, [original.query], 2)
    assert (
        rule(
            1,
            [claim("src/c.py", Evidence(signal="assessed", detail="fact", source="ignored"))],
            mode=ModelMode.ASSESS,
        ).answer_units
        == 2
    )
    with pytest.raises(ValueError, match="share one original rule"):
        original.combined(
            rule(1, [claim("src/c.py", Evidence(signal="other", detail="fact", source="ignored"))])
        )


def test_planner_splits_candidates_without_losing_positions() -> None:
    """Output pressure bisects candidates and preserves their original positions."""
    original = rule(
        0,
        [
            claim("src/same.py", Evidence(signal=name, detail="fact", source="ignored"))
            for name in ("first", "second", "third")
        ],
    )

    packs = planner(output_budget=2200).plan([original])

    assert sorted(position for pack in packs for position in pack.rules[0].positions) == [0, 1, 2]
    assert all(pack.answer_units == 1 for pack in packs)


def test_planner_bounds_the_number_of_judgments_in_one_response() -> None:
    """A large output allowance cannot create an operationally broad model turn."""
    original = rule(
        0,
        [
            claim("src/same.py", Evidence(signal=str(index), detail="fact", source="ignored"))
            for index in range(5)
        ],
    )

    packs = planner(candidate_budget=2, output_budget=384_000).plan([original])

    assert sorted(position for pack in packs for position in pack.rules[0].positions) == list(
        range(5)
    )
    assert all(pack.answer_rows <= 2 for pack in packs)


def test_planner_preserves_transitive_dependencies_and_refills_capacity() -> None:
    """Transitive evidence groups can still share one verified request when capacity permits."""
    first = rule(0, [claim("src/a.py", Evidence(signal="a", detail="left", source="ignored"))])
    bridge = rule(
        1,
        [
            ModelCandidate(
                fact_id="bridge",
                path="src/bridge.py",
                subject="bridge",
                evidence=[
                    Evidence(signal="a", detail="left", source="src/a.py"),
                    Evidence(signal="b", detail="right", source="src/b.py"),
                ],
            )
        ],
    )
    second = rule(2, [claim("src/b.py", Evidence(signal="b", detail="right", source="ignored"))])
    independent = rule(
        3, [claim("tests/c.py", Evidence(signal="c", detail="fact", source="ignored"))]
    )

    packed = planner().plan([first, bridge, second, independent])

    assert len(packed) == 1
    assert [item.index for item in packed[0].rules] == [0, 1, 2, 3]
    assert len(packed[0].protocol.evidence.payloads) == 3


def test_planner_splits_exact_input_by_repository_area() -> None:
    """An exact overrun follows stable path ownership before candidate cardinality."""
    rules = [
        rule(
            index,
            [claim(path, Evidence(signal=signal, detail=detail * 4000, source="ignored"))],
        )
        for index, path, signal, detail in (
            (0, "src/package/a.py", "source", "a"),
            (1, "tests/package/a.py", "test", "b"),
        )
    ]
    counter = OptimisticCounter(model="vendor/model")
    generous = planner(counter=counter)
    budget = max(request_tokens(generous, openrouter.RepositoryPack.of([item])) for item in rules)

    packs = planner(prompt_budget=budget, counter=counter).plan(rules)

    assert len(packs) == 2
    assert sorted(item.index for pack in packs for item in pack.rules) == [0, 1]


def test_planner_splits_estimated_input_by_repository_area() -> None:
    """Provisional sizing separates path owners before exact tokenization."""
    original = rule(
        0,
        [
            claim("src/package/a.py", Evidence(signal="source", detail="a" * 4000, source="x")),
            claim("tests/package/a.py", Evidence(signal="test", detail="b" * 4000, source="x")),
        ],
    )

    packs = planner(prompt_budget=9_000).plan([original])

    assert len(packs) == 2
    assert sorted(position for pack in packs for position in pack.rules[0].positions) == [0, 1]


def test_planner_reserves_reasoning_before_visible_answers() -> None:
    """Maximum effort retains enough allowance for compact structured output."""
    candidate_rule = rule(
        0, [claim("src/a.py", Evidence(signal="a", detail="fact", source="ignored"))]
    )
    exact = planner(output_budget=200_000, effort="max")

    assert exact.reasoning_tokens == 32_000
    assert exact.maximum_output_tokens == 200_000
    assert exact.output_tokens(openrouter.RepositoryPack.of([candidate_rule])) == 34_152
    assert planner().output_tokens(openrouter.RepositoryPack.of([candidate_rule])) is None
    assert len(exact.plan([candidate_rule])) == 1
    with pytest.raises(ValueError, match="One contextual candidate exceeds"):
        planner(output_budget=34_000, effort="max").plan([candidate_rule])


def test_request_tokens_uses_the_official_deepseek_tokenizer_when_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek requests use model tokens while unknown models use a byte ceiling."""

    def encode(sequence: str) -> SimpleNamespace:
        assert sequence == '{"input":"hello"}'
        return SimpleNamespace(ids=[10, 20, 30])

    def from_pretrained(identifier: str) -> SimpleNamespace:
        assert identifier == "deepseek-ai/DeepSeek-V4-Flash"
        return SimpleNamespace(encode=encode)

    def controlled_import(name: str) -> SimpleNamespace:
        assert name == "tokenizers"
        return SimpleNamespace(Tokenizer=SimpleNamespace(from_pretrained=from_pretrained))

    monkeypatch.setattr(
        "mcmr.execution.backends.openrouter.accounting.tokens.import_module",
        controlled_import,
    )
    request: dict[str, JsonValue] = {"input": "hello"}

    assert openrouter.RequestTokens(model="deepseek/deepseek-v4-flash-0731").count(request) == 3
    assert openrouter.RequestTokens(model="deepseek/deepseek-v4-flash-0731").estimate(request) == 6
    assert openrouter.RequestTokens(model="vendor/model").count(request) == 17
    assert openrouter.RequestTokens(model="vendor/model").estimate(request) == 17


def test_exact_verification_overrides_an_optimistic_estimate() -> None:
    """A low estimate cannot let a final request cross its hard token limit."""
    rules = [
        rule(
            index,
            [claim(path, Evidence(signal=signal, detail=detail * 1000, source="ignored"))],
        )
        for index, path, signal, detail in (
            (0, "src/package/a.py", "source", "a"),
            (1, "src/package/b.py", "test", "b"),
        )
    ]
    counter = OptimisticCounter(model="vendor/model")
    generous = planner(counter=counter)
    budget = max(request_tokens(generous, openrouter.RepositoryPack.of([item])) for item in rules)

    packs = planner(prompt_budget=budget, counter=counter).plan(rules)

    assert len(packs) == 2
    assert all(request_tokens(generous, pack) <= budget for pack in packs)


def test_one_irreducible_candidate_cannot_cross_the_input_limit() -> None:
    """Exact verification never silently accepts an irreducible overrun."""
    candidate_rule = rule(
        0, [claim("src/a.py", Evidence(signal="a", detail="fact", source="ignored"))]
    )

    with pytest.raises(ValueError, match="One contextual candidate exceeds"):
        planner(
            prompt_budget=1,
            counter=OptimisticCounter(model="vendor/model"),
        ).plan([candidate_rule])
