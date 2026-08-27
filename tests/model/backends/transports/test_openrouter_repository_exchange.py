import pytest
from httpx2 import ConnectError, MockTransport, ReadError, Request, Response
from pydantic import JsonValue, TypeAdapter

from mcmr.contextual.evaluation import ContextualSweep
from mcmr.execution import OpenRouterBackend, answer_many
from mcmr.execution.queries import ModelMode, ModelQuery
from mcmr.plugins import Fact

from ...backend_values import cited, criteria, payload
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


def repository_query() -> ModelQuery[Category]:
    """Build one contextual repository query with controlled evidence."""
    return ModelQuery.classify(
        ContextualSweep.table(Fact, "ALL-DEMO2001"),
        category=Category,
        instructions="Judge the retained structure.",
    )


@pytest.mark.anyio
async def test_repository_rules_share_one_current_response_request() -> None:
    """Independent contextual rules share one closed repository exchange and its exact cost."""
    query = repository_query()
    probe = RouterProbe(
        RouterProbe.completion(
            {
                "q0": {
                    "v": [["supported"]],
                    "p": [0.75],
                    "d": [],
                },
                "q1": {
                    "v": [["yes", "no"]],
                    "p": [0.8],
                    "d": [{"a": "a1", "r": "The retained structure lacks the second predicate."}],
                },
            }
        )
    )

    resolved = await answer_many(
        OpenRouterBackend(
            transport=probe.transport,
            max_output_tokens=32_000,
            minimum_confidence=0.9,
            reasoning_effort="medium",
        ),
        [query, assessed(query)],
    )

    assert len(probe.requests) == 1
    assert request_format_name(probe) == "repository_rules"
    assert probe.sent()["max_output_tokens"] == 32_000
    assert TypeAdapter(str).validate_python(probe.sent()["session_id"]).startswith("mcmr-")
    assert sum(spend.tokens for result in resolved for spend in result.spend.values()) == 19
    assert [
        result.query.values.collect().get_column("category_value").item() for result in resolved
    ] == ["uncertain", "uncertain"]


@pytest.mark.anyio
async def test_repository_contract_drift_retries_on_a_fresh_session() -> None:
    """A completed response with wrong identities gets one fresh repair attempt."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        request.read()
        requests.append(request)
        answer: JsonValue = (
            {"unexpected": payload()}
            if len(requests) == 1
            else {
                "q0": {
                    "v": [["supported"]],
                    "p": [0.75],
                    "d": [],
                }
            }
        )
        return RouterProbe.streaming(RouterProbe.completion(answer))

    resolved = await OpenRouterBackend(
        transport=MockTransport(respond),
    ).answered_many([repository_query()])
    sessions = [
        TypeAdapter(dict[str, JsonValue]).validate_json(item.content)["session_id"]
        for item in requests
    ]

    assert len(resolved) == 1
    assert len(requests) == 2
    assert sessions[1] == f"{sessions[0]}-contract-1"


@pytest.mark.anyio
async def test_repository_transport_failure_stops_without_request_fanout() -> None:
    """A failed packed turn stops once instead of multiplying an unavailable service."""
    requests: list[Request] = []

    def flaky_respond(request: Request) -> Response:
        requests.append(request)
        if len(requests) == 1:
            raise ConnectError("refused")
        return RouterProbe.streaming(RouterProbe.completion(payload()))

    with pytest.raises(RuntimeError, match="OpenRouter could not answer"):
        await OpenRouterBackend(
            transport=MockTransport(flaky_respond),
            batch_size=1,
        ).answered_many([repository_query(), repository_query()])

    assert len(requests) == 1


@pytest.mark.anyio
async def test_malformed_response_json_retries_once() -> None:
    """A truncated successful envelope gets one bounded retry of the identical request."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        requests.append(request)
        if len(requests) == 1:
            return Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=b'data: {"output":\n\n',
            )
        return RouterProbe.streaming(RouterProbe.completion(payload()))

    answer = await OpenRouterBackend(
        transport=MockTransport(respond),
    ).classify_candidate(cited(), category=Category, instructions="Judge the retained structure.")

    assert answer.value is Category.SUPPORTED
    assert len(requests) == 2


@pytest.mark.anyio
async def test_interrupted_response_stream_retries_once_on_a_fresh_session() -> None:
    """A provider stream reset gets one fresh route without broad connection retries."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        request.read()
        requests.append(request)
        if len(requests) == 1:
            raise ReadError("response stream reset", request=request)
        return RouterProbe.streaming(
            RouterProbe.completion(
                {
                    "q0": {
                        "v": [["supported"]],
                        "p": [0.75],
                        "d": [],
                    }
                }
            )
        )

    resolved = await OpenRouterBackend(
        transport=MockTransport(respond),
    ).answered_many([repository_query()])
    sessions = [
        TypeAdapter(dict[str, JsonValue]).validate_json(item.content).get("session_id")
        for item in requests
    ]

    assert len(resolved) == 1
    assert len(requests) == 2
    assert sessions[1] == f"{sessions[0]}-retry"


@pytest.mark.anyio
async def test_persistently_malformed_response_json_stops_after_one_retry() -> None:
    """Repeated envelope corruption fails instead of creating unbounded requests."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        requests.append(request)
        return Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"output":\n\n',
        )

    with pytest.raises(RuntimeError, match="malformed response JSON"):
        await OpenRouterBackend(
            transport=MockTransport(respond),
        ).classify_candidate(
            cited(), category=Category, instructions="Judge the retained structure."
        )

    assert len(requests) == 2


@pytest.mark.anyio
async def test_failed_repository_response_retries_on_a_fresh_session() -> None:
    """A transient provider failure gets one retry without sticky routing to that endpoint."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        request.read()
        requests.append(request)
        if len(requests) == 1:
            return RouterProbe.streaming(
                {"status": "failed", "error": {"message": "stream failed"}}
            )
        return RouterProbe.streaming(
            RouterProbe.completion(
                {
                    "q0": {
                        "v": [["supported"]],
                        "p": [0.75],
                        "d": [],
                    }
                }
            )
        )

    resolved = await OpenRouterBackend(
        transport=MockTransport(respond),
    ).answered_many([repository_query()])
    sessions = [
        TypeAdapter(dict[str, JsonValue]).validate_json(item.content)["session_id"]
        for item in requests
    ]

    assert len(resolved) == 1
    assert sessions[1] == f"{sessions[0]}-retry"


@pytest.mark.anyio
async def test_a_completed_response_without_output_retries_once() -> None:
    """A transient empty completion gets one fresh attempt before it is rejected."""
    requests: list[Request] = []

    def respond(request: Request) -> Response:
        requests.append(request)
        return RouterProbe.streaming({"output": []})

    with pytest.raises(RuntimeError, match="no answer"):
        await OpenRouterBackend(
            transport=MockTransport(respond),
        ).classify_candidate(
            cited(), category=Category, instructions="Judge the retained structure."
        )

    assert len(requests) == 2
