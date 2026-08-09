import polars as pl
import pytest
from httpx import ConnectError, MockTransport, Request, Response
from pydantic import JsonValue, TypeAdapter

from mcmr.contextual.evaluation import ContextualSweep
from mcmr.execution import CriterionValue, ModelCandidate, OpenRouterBackend, answer_many
from mcmr.execution.backends import CandidateProtocol
from mcmr.execution.queries import ModelMode, ModelQuery
from mcmr.facts import Evidence
from mcmr.plugins import Fact

from ...backend_values import assessment_payload, candidate, cited, criteria, payload
from ...fakes import Category, RouterProbe


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every request a controlled key that never leaves the environment."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def request_format_name(probe: RouterProbe, index: int = 0) -> str:
    """Read the strict output format name from one controlled request."""
    text = TypeAdapter(dict[str, JsonValue]).validate_python(probe.sent(index)["text"])
    format_document = TypeAdapter(dict[str, JsonValue]).validate_python(text["format"])
    return TypeAdapter(str).validate_python(format_document["name"])


def assessed(query: ModelQuery[Category]) -> ModelQuery[Category]:
    """Turn one controlled classification relation into a predicate assessment relation."""
    return ModelQuery(
        candidates=query.candidates,
        category=Category,
        instructions="Assess the retained structure.",
        mode=ModelMode.ASSESS,
        criteria=list(criteria()),
        decision_table=[],
        default=Category.UNCERTAIN,
        uncertain=Category.UNCERTAIN,
    )


@pytest.mark.anyio
async def test_a_valid_completion_becomes_one_cited_and_accounted_classification() -> None:
    """One live-shaped completion becomes one auditable classification."""
    probe = RouterProbe(RouterProbe.completion(payload()))
    backend = OpenRouterBackend(transport=probe.transport, model="vendor/model")

    answer = await backend.classify_candidate(
        cited(), category=Category, instructions="Judge only the retained structure."
    )

    assert (answer.value, answer.evidence, answer.confidence) == (
        Category.SUPPORTED,
        ["structure"],
        0.75,
    )
    assert (answer.provenance.backend, answer.provenance.model) == (
        "openrouter",
        "vendor/model-served",
    )
    assert (
        answer.provenance.input_tokens,
        answer.provenance.cached_input_tokens,
        answer.provenance.output_tokens,
        answer.provenance.reasoning_tokens,
    ) == (12, 3, 4, 2)


@pytest.mark.anyio
async def test_one_authorized_request_carries_the_closed_schema() -> None:
    """The client spends one bounded request on a schema-constrained prompt."""
    probe = RouterProbe(RouterProbe.completion(payload()))
    backend = OpenRouterBackend(
        transport=probe.transport,
        model="vendor/model",
        reasoning_effort="high",
        max_output_tokens=4096,
    )

    await backend.classify_candidate(
        cited(), category=Category, instructions="Judge only the retained structure."
    )

    protocol = CandidateProtocol(
        candidate=cited(),
        instructions="Judge only the retained structure.",
    )
    sent = probe.sent()
    assert (sent["model"], sent["reasoning"], sent["max_output_tokens"]) == (
        "vendor/model",
        {"effort": "high"},
        4096,
    )
    assert sent["plugins"] == [{"id": "response-healing"}]
    assert sent["text"] == {
        "format": {
            "type": "json_schema",
            "name": "classification",
            "strict": True,
            "schema": protocol.classification_schema(Category),
        }
    }
    assert sent["input"] == [{"role": "user", "content": protocol.classification_prompt(Category)}]
    assert (probe.authorization(), str(probe.requests[0].url)) == (
        "Bearer test-key",
        "https://openrouter.ai/api/v1/responses",
    )


@pytest.mark.anyio
async def test_batches_reach_the_server_once_and_split_their_reported_usage() -> None:
    """Both model modes answer a bounded batch in one request and account for its tokens once."""
    cases = [
        candidate(Evidence(signal="first", detail="one", source="first.py")),
        candidate(Evidence(signal="second", detail="two", source="second.py")),
    ]
    classified = RouterProbe(
        RouterProbe.batched([payload(evidence=("first",)), payload(evidence=("second",))])
    )
    assessed = RouterProbe(
        RouterProbe.batched(
            [assessment_payload(evidence="first"), assessment_payload(evidence="second")]
        )
    )

    answers = await OpenRouterBackend(transport=classified.transport, batch_size=2).classify_many(
        cases, category=Category, instructions="Judge each structure."
    )
    predicates = await OpenRouterBackend(transport=assessed.transport, batch_size=2).assess_many(
        cases, criteria=criteria(), instructions="Assess each structure."
    )

    assert ([answer.evidence for answer in answers], len(classified.requests)) == (
        [["first"], ["second"]],
        1,
    )
    assert [answer.value("structure supported") for answer in predicates] == [
        CriterionValue.YES,
        CriterionValue.YES,
    ]
    assert sum(answer.provenance.input_tokens for answer in answers) == 12
    assert "reasoning" not in classified.sent()


@pytest.mark.anyio
async def test_repository_rules_share_one_current_response_request() -> None:
    """Independent contextual rules share one closed repository exchange and its exact cost."""
    query = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )
    identifier = next(
        iter(ModelCandidate.from_row(query.candidates.collect().to_dicts()[0]).retained)
    )
    classified: JsonValue = {"answers": {"0": payload(evidence=(identifier,))}}
    predicates: JsonValue = {"answers": {"0": assessment_payload(evidence=identifier)}}
    probe = RouterProbe(RouterProbe.completion({"answers": {"0": classified, "1": predicates}}))

    resolved = await answer_many(
        OpenRouterBackend(transport=probe.transport),
        [query, assessed(query)],
    )

    assert len(probe.requests) == 1
    assert request_format_name(probe) == "repository_rules"
    assert sum(spend.tokens for result in resolved for spend in result.spend.values()) == 19


@pytest.mark.anyio
async def test_repository_transport_failure_bisects_before_retrying_rules() -> None:
    """A failed packed turn retries smaller groups through their isolated rule protocol."""
    query = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )
    requests: list[Request] = []

    def flaky_respond(request: Request) -> Response:
        requests.append(request)
        if len(requests) == 1:
            raise ConnectError("refused")
        return Response(200, json=RouterProbe.completion(payload()))

    resolved = await OpenRouterBackend(
        transport=MockTransport(flaky_respond),
        batch_size=1,
    ).answered_many([query, query])

    assert len(resolved) == 2
    assert len(requests) == 5


@pytest.mark.anyio
async def test_empty_repository_rules_never_reach_openrouter() -> None:
    """Collected rules with no candidates resolve locally before packing."""
    query = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )
    empty = query.model_copy(update={"candidates": query.candidates.filter(pl.lit(False))})
    probe = RouterProbe(RouterProbe.completion(payload()))

    resolved = await OpenRouterBackend(transport=probe.transport).answered_many([empty])

    assert len(resolved) == 1
    assert probe.requests == []


@pytest.mark.anyio
async def test_invalid_repository_keys_bisect_and_leave_each_rule_isolated() -> None:
    """A malformed packed envelope retries only smaller groups through existing isolation."""
    query = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )
    identifier = next(
        iter(ModelCandidate.from_row(query.candidates.collect().to_dicts()[0]).retained)
    )
    probe = RouterProbe(
        RouterProbe.completion({"answers": {"unexpected": payload(evidence=(identifier,))}})
    )

    resolved = await OpenRouterBackend(transport=probe.transport).answered_many([query, query])

    assert len(resolved) == 2
    assert len(probe.requests) == 5


@pytest.mark.anyio
async def test_an_oversized_repository_group_bisects_to_isolated_rule_batches() -> None:
    """A conservative prompt budget splits rules without losing their existing fallback path."""
    query = ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )
    identifier = next(
        iter(ModelCandidate.from_row(query.candidates.collect().to_dicts()[0]).retained)
    )
    probe = RouterProbe(
        RouterProbe.completion({"answers": {"0": payload(evidence=(identifier,))}})
    )

    resolved = await OpenRouterBackend(
        transport=probe.transport,
        prompt_token_budget=1,
    ).answered_many([query, query])

    assert len(resolved) == 2
    assert len(probe.requests) == 2
    assert {request_format_name(probe, index) for index in range(2)} == {"classification"}


@pytest.mark.anyio
async def test_an_empty_relation_never_reaches_the_server() -> None:
    """An empty contextual relation remains an empty result in both model modes."""
    probe = RouterProbe(RouterProbe.completion(payload()))
    backend = OpenRouterBackend(transport=probe.transport)

    assert await backend.classify_many([], category=Category, instructions="Judge.") == []
    assert await backend.assess_many([], criteria=criteria(), instructions="Assess.") == []
    assert probe.requests == []


@pytest.mark.anyio
async def test_a_missing_key_refuses_the_request_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A backend without credentials explains itself instead of calling an anonymous server."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    probe = RouterProbe(RouterProbe.completion(payload()))
    backend = OpenRouterBackend(transport=probe.transport)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await backend.classify_candidate(
            candidate(), category=Category, instructions="Judge the structure."
        )
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await backend.classify_many(
            [candidate()], category=Category, instructions="Judge the structure."
        )

    assert probe.requests == []


@pytest.mark.anyio
async def test_one_answering_batch_keeps_a_dead_one_isolated() -> None:
    """A batch whose turn never reached the server stays isolated once another batch proves it."""
    live = cited()
    dead = candidate(Evidence(signal="dead", detail="one", source="dead.py"))
    requests: list[Request] = []

    def flaky_respond(request: Request) -> Response:
        requests.append(request)
        if len(requests) == 1:
            raise ConnectError("refused")
        return Response(200, json=RouterProbe.batched([payload()]))

    backend = OpenRouterBackend(transport=MockTransport(flaky_respond), batch_size=1)

    answers = await backend.classify_many(
        [dead, live], category=Category, instructions="Judge the structure."
    )

    assert [answer.value for answer in answers] == [Category.UNCERTAIN, Category.SUPPORTED]
    assert "could not answer" in answers[0].reasoning
    assert len(requests) == 2


@pytest.mark.anyio
async def test_a_call_where_every_batch_dies_raises_instead_of_reporting_uncertainty() -> None:
    """A run that never once reached the server surfaces its failure instead of hiding it."""
    probe = RouterProbe(RouterProbe.completion(payload()), failure=ConnectError("refused"))
    backend = OpenRouterBackend(transport=probe.transport, batch_size=1)
    cases = [
        candidate(Evidence(signal="first", detail="one", source="first.py")),
        candidate(Evidence(signal="second", detail="one", source="second.py")),
    ]

    with pytest.raises(RuntimeError, match="could not answer"):
        await backend.classify_many(cases, category=Category, instructions="Judge the structure.")


@pytest.mark.anyio
async def test_an_assessment_call_where_every_batch_dies_raises_too() -> None:
    """The same total-outage escalation covers the assessment lane, not only classification."""
    probe = RouterProbe(RouterProbe.completion(payload()), failure=ConnectError("refused"))
    backend = OpenRouterBackend(transport=probe.transport, batch_size=1)
    cases = [
        candidate(Evidence(signal="first", detail="one", source="first.py")),
        candidate(Evidence(signal="second", detail="one", source="second.py")),
    ]

    with pytest.raises(RuntimeError, match="could not answer"):
        await backend.assess_many(cases, criteria=criteria(), instructions="Assess the structure.")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("probe", "message"),
    [
        (RouterProbe({"error": {"message": "no credits"}}, status_code=402), "402"),
        (RouterProbe("<html>gateway</html>", status_code=503), "gateway"),
        (RouterProbe("not json at all"), "could not answer"),
        (RouterProbe({"output": []}), "no answer"),
        (
            RouterProbe(
                {
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "  "}]}
                    ]
                }
            ),
            "no answer",
        ),
        (
            RouterProbe(RouterProbe.completion(payload()), failure=ConnectError("refused")),
            "could not answer",
        ),
    ],
)
async def test_every_unusable_response_raises_one_bounded_diagnostic(
    probe: RouterProbe,
    message: str,
) -> None:
    """A transport, status, or shape failure never masquerades as a classification."""
    with pytest.raises(RuntimeError, match=message):
        await OpenRouterBackend(transport=probe.transport).classify_candidate(
            candidate(), category=Category, instructions="Judge the structure."
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "usage",
    [None, {}, {"input_tokens": -3, "output_tokens": "4"}],
    ids=["absent", "empty", "invalid"],
)
async def test_absent_or_invalid_telemetry_never_invents_counts(usage: JsonValue) -> None:
    """An unreported usage record stays honest and keeps the configured model name."""
    body = RouterProbe.completion(payload(), model="   ", usage=usage)
    if usage is None:
        del body["usage"]
    probe = RouterProbe(body)

    answer = await OpenRouterBackend(
        transport=probe.transport, model="configured/model"
    ).classify_candidate(cited(), category=Category, instructions="Judge the structure.")

    assert answer.provenance.model == "configured/model"
    assert (
        answer.provenance.input_tokens,
        answer.provenance.cached_input_tokens,
        answer.provenance.output_tokens,
        answer.provenance.reasoning_tokens,
    ) == (0, 0, 0, 0)
