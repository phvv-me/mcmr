import json
import os
from typing import TYPE_CHECKING

from httpx import AsyncBaseTransport, AsyncClient, ReadError, ReadTimeout, RemoteProtocolError
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, omit
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseInputParam,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseStreamEvent,
    ResponseTextConfigParam,
    ResponseTextDeltaEvent,
)
from openai.types.shared_params import Reasoning
from patos import FrozenModel
from pydantic import Field, InstanceOf, JsonValue, PositiveInt, TypeAdapter, ValidationError

from ....domain.contracts import ModelProvenance
from ....domain.primitives import NonEmptyStr
from ...report import JsonReport
from .transport import RetryableResponseError, StreamObserver, StreamPhase

if TYPE_CHECKING:
    from collections.abc import Mapping


class OpenRouterClient(FrozenModel):
    """Run one schema-constrained response through the official OpenAI client."""

    server: NonEmptyStr = "https://openrouter.ai/api/v1"
    model: NonEmptyStr = "anthropic/claude-sonnet-5"
    reasoning_effort: NonEmptyStr = "none"
    timeout_seconds: int = Field(default=180, ge=1)
    max_output_tokens: PositiveInt | None = None
    transport: InstanceOf[AsyncBaseTransport] | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    def answer(self, completion: Mapping[str, JsonValue]) -> str:
        """Read the first structured output text one completed response carries."""
        if answer := self._output_text(completion):
            return answer
        raise RuntimeError(f"OpenRouter returned no answer. {json.dumps(completion)[:500]}")

    def body(
        self,
        schema_document: Mapping[str, JsonValue],
        *,
        cache_key: str | None = None,
        max_output_tokens: PositiveInt | None = None,
        prompt: str,
        name: str,
    ) -> dict[str, JsonValue]:
        """Build one current OpenAI-compatible request that closes the answer schema."""
        body: dict[str, JsonValue] = {
            "model": self.model,
            "input": [{"role": "user", "content": prompt}],
            "plugins": [{"id": "response-healing"}],
            "provider": {"require_parameters": True},
            "stream": True,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "strict": True,
                    "schema": dict(schema_document),
                },
            },
        }
        if self.reasoning_effort != "none":
            body["reasoning"] = {"effort": self.reasoning_effort}
        output_limit = self.max_output_tokens if max_output_tokens is None else max_output_tokens
        if output_limit is not None:
            body["max_output_tokens"] = output_limit
        if cache_key is not None:
            body["session_id"] = cache_key
        return body

    async def exchange(
        self,
        client: AsyncOpenAI,
        request: Mapping[str, JsonValue],
        observer: StreamObserver | None = None,
    ) -> dict[str, JsonValue]:
        """Post once and retry one interrupted or incomplete response on a fresh route."""
        try:
            return await self._exchange_once(client, request, observer)
        except json.JSONDecodeError, RetryableResponseError:
            return await self._retry(client, request, observer)
        except APIConnectionError as error:
            return await self._recover_connection(error, client, request, observer)

    async def invoke(
        self,
        schema_document: Mapping[str, JsonValue],
        *,
        cache_key: str | None = None,
        max_output_tokens: PositiveInt | None = None,
        prompt: str,
        name: str,
        observer: StreamObserver | None = None,
    ) -> tuple[str, ModelProvenance]:
        """Run one structured completion and return its answer source with its provenance."""
        request = self.body(
            schema_document,
            cache_key=cache_key,
            max_output_tokens=max_output_tokens,
            prompt=prompt,
            name=name,
        )
        http_client = AsyncClient(
            base_url=self.server,
            timeout=self.timeout_seconds,
            transport=self.transport,
        )
        async with AsyncOpenAI(
            api_key=self.key(),
            base_url=self.server,
            http_client=http_client,
            max_retries=0,
            timeout=self.timeout_seconds,
        ) as client:
            try:
                completion = await self.exchange(client, request, observer)
            except json.JSONDecodeError as error:
                raise RuntimeError("OpenRouter returned malformed response JSON") from error
            except (APIError, RetryableResponseError, ValidationError) as error:
                raise RuntimeError(f"OpenRouter could not answer. {error!r}"[:500]) from error
        return self.answer(completion), self.provenance(completion)

    def key(self) -> str:
        """Read the request key from the environment so no configuration ever holds it."""
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OpenRouter needs the `OPENROUTER_API_KEY` environment variable")
        return key

    def provenance(self, completion: Mapping[str, JsonValue]) -> ModelProvenance:
        """Turn one completion's reported usage into shared, nonnegative model provenance."""
        report = JsonReport(document=dict(completion))
        usage = report.group("usage")
        return ModelProvenance(
            backend="openrouter",
            model=report.text("model") or self.model,
            reasoning_effort=self.reasoning_effort,
            input_tokens=usage.count("input_tokens"),
            cached_input_tokens=usage.group("input_tokens_details").count("cached_tokens"),
            output_tokens=usage.count("output_tokens"),
            reasoning_tokens=usage.group("output_tokens_details").count("reasoning_tokens"),
        )

    @staticmethod
    def _completed(
        completion: dict[str, JsonValue],
        observer: StreamObserver | None,
    ) -> dict[str, JsonValue]:
        """Validate one final response before reporting its request as completed."""
        validated = OpenRouterClient._validated(completion)
        if observer is not None:
            observer(StreamPhase.COMPLETED, 0)
        return validated

    @staticmethod
    def _document(value: JsonValue) -> dict[str, JsonValue]:
        """Validate one SDK model dump as the shared JSON document type."""
        return TypeAdapter(dict[str, JsonValue]).validate_python(value)

    @staticmethod
    def _failure(completion: Mapping[str, JsonValue]) -> str:
        """Describe one incomplete response without repeating partial generated content."""
        report = JsonReport(document=dict(completion))
        diagnostic = (
            report.group("error").text("message")
            or report.group("incomplete_details").text("reason")
            or "no failure reason was reported"
        )
        return f"OpenRouter response ended with {report.text('status')}. {diagnostic}"[:500]

    @staticmethod
    def _interrupted(error: APIConnectionError) -> bool:
        """Distinguish a started stream reset from a connection that never opened."""
        return isinstance(error, APITimeoutError) or isinstance(
            error.__cause__,
            (ReadError, ReadTimeout, RemoteProtocolError),
        )

    @staticmethod
    def _observe(event: ResponseStreamEvent, observer: StreamObserver | None) -> None:
        """Translate typed SDK events into stable progress phases."""
        if observer is None:
            return
        if isinstance(event, ResponseCreatedEvent):
            observer(StreamPhase.CONNECTED, 0)
        elif isinstance(
            event,
            (ResponseReasoningSummaryTextDeltaEvent, ResponseReasoningTextDeltaEvent),
        ):
            observer(StreamPhase.REASONING, len(event.delta.encode()))
        elif isinstance(event, ResponseTextDeltaEvent):
            observer(StreamPhase.GENERATING, len(event.delta.encode()))

    @staticmethod
    def _output_text(completion: Mapping[str, JsonValue]) -> str:
        """Read structured output text without assuming a provider returned content."""
        output = completion.get("output")
        for item in output if isinstance(output, list) else []:
            message = JsonReport(document=item if isinstance(item, dict) else {})
            content = message.document.get("content")
            for part in content if isinstance(content, list) else []:
                text = JsonReport(document=part if isinstance(part, dict) else {})
                if text.text("type") == "output_text" and (answer := text.text("text")):
                    return answer
        return ""

    @staticmethod
    def _validated(completion: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Require a final response to carry the same completed status as JSON mode."""
        report = JsonReport(document=completion)
        if (status := report.text("status")) and status != "completed":
            raise RetryableResponseError(OpenRouterClient._failure(completion))
        if not OpenRouterClient._output_text(completion):
            raise RetryableResponseError("OpenRouter completed with no answer")
        return completion

    async def _exchange_once(
        self,
        client: AsyncOpenAI,
        request: Mapping[str, JsonValue],
        observer: StreamObserver | None,
    ) -> dict[str, JsonValue]:
        """Read one typed Responses stream and retain its completed response."""
        input_items = TypeAdapter(ResponseInputParam).validate_python(request["input"])
        text = TypeAdapter(ResponseTextConfigParam).validate_python(request["text"])
        reasoning = (
            TypeAdapter(Reasoning).validate_python(request["reasoning"])
            if "reasoning" in request
            else omit
        )
        output_limit = (
            TypeAdapter(PositiveInt).validate_python(request["max_output_tokens"])
            if "max_output_tokens" in request
            else omit
        )
        extra_body = {
            key: request[key] for key in ("plugins", "provider", "session_id") if key in request
        }
        stream = await client.responses.create(
            model=self.model,
            input=input_items,
            max_output_tokens=output_limit,
            reasoning=reasoning,
            stream=True,
            text=text,
            extra_body=extra_body,
        )
        completed: dict[str, JsonValue] | None = None
        async with stream:
            async for event in stream:
                self._observe(event, observer)
                if isinstance(event, ResponseCompletedEvent):
                    completed = self._document(
                        event.response.model_dump(mode="json", warnings=False)
                    )
                elif isinstance(event, ResponseErrorEvent):
                    diagnostic = f"OpenRouter stream failed. {event.message}"[:500]
                    raise RetryableResponseError(diagnostic)
                elif isinstance(event, (ResponseFailedEvent, ResponseIncompleteEvent)):
                    document = self._document(
                        event.response.model_dump(mode="json", warnings=False)
                    )
                    raise RetryableResponseError(self._failure(document))
        if completed is None:
            raise RetryableResponseError("OpenRouter stream ended without a completed response")
        return self._completed(completed, observer)

    async def _recover_connection(
        self,
        error: APIConnectionError,
        client: AsyncOpenAI,
        request: Mapping[str, JsonValue],
        observer: StreamObserver | None,
    ) -> dict[str, JsonValue]:
        """Retry a started stream reset while preserving immediate connection failures."""
        if not self._interrupted(error):
            raise error
        return await self._retry(client, request, observer)

    async def _retry(
        self,
        client: AsyncOpenAI,
        request: Mapping[str, JsonValue],
        observer: StreamObserver | None,
    ) -> dict[str, JsonValue]:
        """Retry one exchange on a fresh route."""
        if observer is not None:
            observer(StreamPhase.RETRYING, 0)
        retried = dict(request)
        if session_id := retried.get("session_id"):
            retried["session_id"] = f"{session_id}-retry"
        return await self._exchange_once(client, retried, observer)
