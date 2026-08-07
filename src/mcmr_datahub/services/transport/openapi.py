from typing import TYPE_CHECKING

import httpx
from pydantic import JsonValue, TypeAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import Self

    from ..settings import DataHubSettings

# How many entities one ingestion request carries, which keeps a large repository's fact tables
# off a single multi-megabyte body without turning each entity into its own round trip.
_BATCH = 50

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])


class DataHubOpenAPI:
    """Ingest entities through the DataHub OpenAPI, which is where an aspect can carry a schema.

    GraphQL exposes the mutations a person performs in the product and has none for declaring a
    dataset, a flow, or a job with the aspects this graph is made of, so publication uses the
    ingestion surface the catalog itself is loaded through. Every request is an upsert keyed by
    the entity URN, which is what lets a scheduled run post the same graph again unchanged.
    """

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Open one reusable connection pool for the publication request."""
        headers = (
            {"Authorization": f"Bearer {token}"}
            if (token := self.settings.token) is not None
            else {}
        )
        self.client = httpx.AsyncClient(
            base_url=f"{str(self.settings.server).rstrip('/')}/",
            headers=headers,
            timeout=self.settings.timeout_seconds,
            transport=self.transport,
        )
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the request-local connection pool."""
        if self.client is not None:
            await self.client.aclose()
        self.client = None

    async def ingest(self, entity: str, entities: Sequence[JsonValue]) -> int:
        """Upsert every stated entity of one type and return how many were written."""
        if self.client is None:
            raise RuntimeError("DataHub OpenAPI client must be opened before use")
        for start in range(0, len(entities), _BATCH):
            response = await self.client.post(
                f"openapi/v3/entity/{entity}",
                params={"async": "false"},
                json=list(entities[start : start + _BATCH]),
            )
            response.raise_for_status()
        return len(entities)

    async def read(self, entity: str, urns: Sequence[str]) -> dict[str, dict[str, JsonValue]]:
        """Return the aspects each stated entity already holds, omitting the ones that do not.

        A rule the whole instance shares is merged rather than overwritten, so publishing one
        repository has to see what every earlier repository already wrote onto it.
        """
        if self.client is None:
            raise RuntimeError("DataHub OpenAPI client must be opened before use")
        held: dict[str, dict[str, JsonValue]] = {}
        for start in range(0, len(urns), _BATCH):
            response = await self.client.post(
                f"openapi/v3/entity/{entity}/batchGet",
                json=[{"urn": urn} for urn in urns[start : start + _BATCH]],
            )
            response.raise_for_status()
            for value in _ENTITIES.validate_python(response.json()):
                held[str(value["urn"])] = value
        return held
