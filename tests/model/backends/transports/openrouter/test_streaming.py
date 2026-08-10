import json
from typing import TYPE_CHECKING

import pytest
from httpx import MockTransport, Request, Response
from pydantic import JsonValue, TypeAdapter

from mcmr.execution.backends import openrouter

from ....fakes import RouterProbe

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every request a controlled key that never leaves the environment."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def response_stream(*events: Mapping[str, JsonValue]) -> Response:
    """Encode typed Responses events as one controlled SSE response."""
    content = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    return Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=f"{content}data: [DONE]\n\n",
    )


def test_answer_reader_rejects_an_unvalidated_empty_response() -> None:
    """The public answer reader still guards callers that bypass exchange validation."""
    with pytest.raises(RuntimeError, match="no answer"):
        openrouter.OpenRouterClient().answer({"output": []})


@pytest.mark.anyio
async def test_official_sdk_events_report_reasoning_and_generation_progress() -> None:
    """The OpenAI client turns real response event types into honest progress phases."""
    completion = RouterProbe.completion({"ok": True})
    stream = response_stream(
        {"type": "response.created", "sequence_number": 0, "response": completion},
        {
            "type": "response.reasoning_text.delta",
            "sequence_number": 1,
            "item_id": "reasoning",
            "output_index": 0,
            "content_index": 0,
            "delta": "think",
        },
        {
            "type": "response.reasoning_summary_text.delta",
            "sequence_number": 2,
            "item_id": "reasoning",
            "output_index": 0,
            "summary_index": 0,
            "delta": "brief",
        },
        {
            "type": "response.output_text.delta",
            "sequence_number": 3,
            "item_id": "answer",
            "output_index": 1,
            "content_index": 0,
            "logprobs": [],
            "delta": '{"ok":true}',
        },
        {"type": "response.completed", "sequence_number": 4, "response": completion},
    )
    events: list[tuple[openrouter.StreamPhase, int]] = []

    answer, provenance = await openrouter.OpenRouterClient(
        model="vendor/model",
        transport=MockTransport(lambda request: stream),
    ).invoke(
        {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
        prompt="Return true.",
        name="stream_test",
        observer=lambda phase, size: events.append((phase, size)),
    )

    assert TypeAdapter(dict[str, bool]).validate_json(answer) == {"ok": True}
    assert provenance.input_tokens == 12
    assert events == [
        (openrouter.StreamPhase.CONNECTED, 0),
        (openrouter.StreamPhase.REASONING, 5),
        (openrouter.StreamPhase.REASONING, 5),
        (openrouter.StreamPhase.GENERATING, 11),
        (openrouter.StreamPhase.COMPLETED, 0),
    ]


@pytest.mark.anyio
async def test_stream_error_retries_once_and_reports_the_retry() -> None:
    """A typed stream error opens one fresh session and exposes the retry phase."""
    requests: list[Request] = []
    responses = [
        response_stream(
            {
                "type": "error",
                "sequence_number": 0,
                "code": "upstream_error",
                "message": "temporary provider failure",
                "param": None,
            }
        ),
        RouterProbe.streaming(RouterProbe.completion({"ok": True})),
    ]

    def respond(request: Request) -> Response:
        request.read()
        requests.append(request)
        return responses.pop(0)

    events: list[tuple[openrouter.StreamPhase, int]] = []
    answer, _ = await openrouter.OpenRouterClient(transport=MockTransport(respond)).invoke(
        {"type": "object"},
        cache_key="stable",
        prompt="Return true.",
        name="stream_retry",
        observer=lambda phase, size: events.append((phase, size)),
    )
    sessions = [
        TypeAdapter(dict[str, JsonValue]).validate_json(request.content)["session_id"]
        for request in requests
    ]

    assert TypeAdapter(dict[str, bool]).validate_json(answer) == {"ok": True}
    assert sessions == ["stable", "stable-retry"]
    assert events == [
        (openrouter.StreamPhase.RETRYING, 0),
        (openrouter.StreamPhase.COMPLETED, 0),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "broken",
    [
        response_stream(),
        response_stream(
            {
                "type": "response.completed",
                "sequence_number": 0,
                "response": {
                    "status": "failed",
                    "error": {"message": "provider stopped"},
                },
            }
        ),
        response_stream(
            {
                "type": "response.completed",
                "sequence_number": 0,
                "response": {
                    **RouterProbe.completion({"ok": True}),
                    "output": [],
                },
            }
        ),
    ],
    ids=["missing-completion", "contradictory-completion", "empty-answer"],
)
async def test_broken_stream_completion_retries_once(broken: Response) -> None:
    """A missing or contradictory completion never becomes a successful answer."""
    requests: list[Request] = []
    events: list[tuple[openrouter.StreamPhase, int]] = []
    responses = [broken, RouterProbe.streaming(RouterProbe.completion({"ok": True}))]

    def respond(request: Request) -> Response:
        requests.append(request)
        return responses.pop(0)

    answer, _ = await openrouter.OpenRouterClient(transport=MockTransport(respond)).invoke(
        {"type": "object"},
        prompt="Return true.",
        name="broken_stream",
        observer=lambda phase, size: events.append((phase, size)),
    )

    assert TypeAdapter(dict[str, bool]).validate_json(answer) == {"ok": True}
    assert len(requests) == 2
    assert events == [
        (openrouter.StreamPhase.RETRYING, 0),
        (openrouter.StreamPhase.COMPLETED, 0),
    ]


def _exercise_progress(progress: openrouter.RepositoryProgress) -> None:
    """Feed two controlled request streams into one aggregate display."""
    first = progress.observer(0)
    second = progress.observer(1)
    first(openrouter.StreamPhase.CONNECTED, 999_999)
    first(openrouter.StreamPhase.REASONING, 2)
    second(openrouter.StreamPhase.RETRYING, 0)
    first(openrouter.StreamPhase.GENERATING, 5)
    first(openrouter.StreamPhase.COMPLETED, 0)
    second(openrouter.StreamPhase.COMPLETED, 0)


def test_repository_progress_aggregates_real_events_without_fake_percentages() -> None:
    """The terminal display counts completed packs and actual response bytes."""
    progress = openrouter.RepositoryProgress(total=2)

    with progress:
        _exercise_progress(progress)

    task = progress.progress.tasks[0]
    assert (task.completed, task.description, task.fields["received"]) == (
        2,
        "DeepSeek finishing",
        "1.0 MB",
    )
