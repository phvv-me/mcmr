import json
from functools import cache
from pathlib import Path

import httpx
from pydantic import JsonValue, TypeAdapter

_exchanges = TypeAdapter(list[dict[str, JsonValue]])

# The one path whose body names its own operation, which every other path spells in its URL.
_GRAPHQL = "/api/graphql"


class RecordedTransport(httpx.AsyncBaseTransport):
    """Replay captured DataHub exchanges so a checkout needs no running service.

    One JSON file per operation holds the exchanges that operation produced, each pairing the
    variables that identify a request with the exact response envelope the server returned. A
    recorded exchange states only the variables that identify it, so a volatile value such as a
    run timestamp never has to be predicted, and an exchange naming none answers the whole
    operation. A live capture appends the envelope verbatim, so re-recording against a real
    endpoint is a file swap rather than a format change.

    A GraphQL request names its operation in its own body. An ingestion request names it in its
    URL instead, so `POST /openapi/v3/entity/dataset` is recorded as `post-openapi-v3-entity-
    dataset.json` and is keyed by nothing, because MCMR reads no field out of the acknowledgment.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Answer one request from the recording that names its operation and variables."""
        if not request.url.path.endswith(_GRAPHQL):
            return httpx.Response(200, json=self._answer(self._route(request), {}))
        payload = TypeAdapter(dict[str, JsonValue]).validate_python(json.loads(request.content))
        operation = payload["operationName"]
        if not isinstance(operation, str):
            raise RuntimeError("a recorded DataHub request must name one operation")
        return httpx.Response(200, json=self._answer(operation, payload.get("variables")))

    @staticmethod
    def _matches(recorded: JsonValue, *, requested: JsonValue) -> bool:
        """Whether a request agrees with every variable its recorded exchange is keyed by."""
        if not isinstance(recorded, dict) or not isinstance(requested, dict):
            return recorded == requested
        return all(requested.get(name) == value for name, value in recorded.items())

    @staticmethod
    @cache
    def _recorded(path: str) -> list[dict[str, JsonValue]]:
        """Parse one recording once, since a run replays the same operation many times."""
        return _exchanges.validate_python(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def _route(request: httpx.Request) -> str:
        """Name one non-GraphQL exchange after the method and path that identify it."""
        return "-".join([request.method.lower(), *request.url.path.strip("/").split("/")])

    def _answer(self, operation: str, variables: JsonValue) -> JsonValue:
        """Return the envelope recorded for the exchange these variables identify."""
        path = self.root / f"{operation}.json"
        if not path.is_file():
            raise RuntimeError(f"the DataHub recording holds no operation {operation}")
        for exchange in self._recorded(str(path)):
            if self._matches(exchange["variables"], requested=variables):
                return exchange["response"]
        raise RuntimeError(f"the DataHub recording of {operation} holds no {variables}")
