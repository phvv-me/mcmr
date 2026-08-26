import json
from typing import TYPE_CHECKING

from httpx2 import HTTPError, MockTransport, Request, Response
from pydantic import JsonValue, TypeAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence


class RouterProbe:
    """Answer OpenRouter responses with controlled bodies and retain every request."""

    def __init__(
        self,
        body: JsonValue | str,
        status_code: int = 200,
        failure: HTTPError | None = None,
    ) -> None:
        self.body = body
        self.status_code = status_code
        self.failure = failure
        self.requests: list[Request] = []

    @property
    def transport(self) -> MockTransport:
        """Answer every request through the controlled handler."""
        return MockTransport(self.respond)

    @staticmethod
    def batched(
        answers: Sequence[JsonValue],
        *,
        model: str = "vendor/model-served",
        usage: JsonValue = None,
    ) -> dict[str, JsonValue]:
        """Build one completion whose single answer keys every candidate in a batch."""
        keyed: JsonValue = {str(index): answer for index, answer in enumerate(answers)}
        return RouterProbe.completion({"answers": keyed}, model=model, usage=usage)

    @staticmethod
    def completion(
        answer: JsonValue,
        *,
        model: str = "vendor/model-served",
        usage: JsonValue = None,
    ) -> dict[str, JsonValue]:
        """Build one OpenAI-compatible response around a structured answer."""
        reported: JsonValue = {
            "input_tokens": 12,
            "input_tokens_details": {"cached_tokens": 3},
            "output_tokens": 4,
            "output_tokens_details": {"reasoning_tokens": 2},
        }
        content = answer if isinstance(answer, str) else json.dumps(answer, sort_keys=True)
        return {
            "id": "gen-controlled",
            "model": model,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": content}],
                }
            ],
            "usage": reported if usage is None else usage,
        }

    @staticmethod
    def streaming(body: JsonValue | str) -> Response:
        """Wrap one controlled answer in the current Responses SSE protocol."""
        if isinstance(body, str):
            content = f"data: {body}\n\n"
        else:
            report = TypeAdapter(dict[str, JsonValue]).validate_python(body)
            status = report.get("status")
            event_type = {
                "failed": "response.failed",
                "incomplete": "response.incomplete",
            }.get(status if isinstance(status, str) else "", "response.completed")
            event = {"type": event_type, "sequence_number": 1, "response": report}
            content = f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n"
        return Response(200, headers={"content-type": "text/event-stream"}, text=content)

    def authorization(self, index: int = 0) -> str:
        """Read the authorization header one recorded request carried."""
        return self.requests[index].headers.get("authorization", "")

    def respond(self, request: Request) -> Response:
        """Retain one recorded request and return its controlled answer."""
        request.read()
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        if self.status_code < 300:
            return self.streaming(self.body)
        if isinstance(self.body, str):
            return Response(self.status_code, text=self.body)
        return Response(self.status_code, json=self.body)

    def sent(self, index: int = 0) -> dict[str, JsonValue]:
        """Read one recorded request body as its validated JSON document."""
        return TypeAdapter(dict[str, JsonValue]).validate_json(self.requests[index].content)
