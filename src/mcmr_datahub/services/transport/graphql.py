from typing import TYPE_CHECKING

from .exceptions import DataHubRequestError
from .response import GraphQLResponse

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

    import httpx
    from pydantic import JsonValue

    from mcmr.plugins import NonEmptyStr

    from ..configuration import DataHubSettings


class DataHubGraphQL:
    """Execute bounded direct GraphQL requests without a local service or cache.

    The pool exists from construction, so there is no opening step a caller can forget and no
    order for the methods to be called in. Entering the block gives the pool a lifetime rather
    than a beginning, and leaving it closes the pool.
    """

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client = settings.connection(transport)

    async def __aenter__(self) -> Self:
        """Hand back the client whose connection pool this block will close."""
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the request-local connection pool."""
        await self.client.aclose()

    async def execute(
        self,
        query: NonEmptyStr,
        variables: dict[str, JsonValue],
        operation: NonEmptyStr,
    ) -> dict[str, JsonValue]:
        """Return validated GraphQL data or fail with the server errors."""
        payload: dict[str, JsonValue] = {
            "query": query,
            "variables": variables,
            "operationName": operation,
        }
        return self._data(await self._answered(payload))

    @staticmethod
    def _data(envelope: GraphQLResponse) -> dict[str, JsonValue]:
        """Read the data one envelope carries, or fail with what the server said went wrong."""
        if envelope.errors:
            raise DataHubRequestError(f"DataHub GraphQL request failed with {envelope.errors}")
        if envelope.data is None:
            raise DataHubRequestError("DataHub GraphQL response omitted data")
        return envelope.data

    async def _answered(self, payload: dict[str, JsonValue]) -> GraphQLResponse:
        """Send one operation to the GraphQL endpoint and read the envelope it answers with."""
        response = await self.client.post("api/graphql", json=payload)
        response.raise_for_status()
        return GraphQLResponse.model_validate(response.json())
