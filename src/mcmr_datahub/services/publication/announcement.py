from typing import TYPE_CHECKING

from ..transport.openapi import DataHubOpenAPI
from .labels import flow_urn

if TYPE_CHECKING:
    import httpx
    from pydantic import JsonValue

    from mcmr.plugins import RunGraph

    from ..configuration import DataHubSettings

# Where DataHub shows one published flow, stated without a host so the link resolves against
# whichever front end the reader already has open.
_PAGE = "/pipelines"


class DataHubAnnouncement:
    """Put one repository's published graph on the DataHub home page.

    Search finds an entity somebody already knows to look for. A home page post is what puts the
    graph in front of somebody who does not, which is why this exists at all. The post is keyed by
    the repository it announces, so a scheduled run rewrites the same card instead of stacking a
    new one beside it, and a project has to ask for the card before any of this runs.
    """

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def publish(self, graph: RunGraph) -> list[str]:
        """Announce this repository's graph once, when the project asked for an announcement."""
        if not self.settings.writeback.announce:
            return []
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            await openapi.ingest("post", [self._post(graph)])
        return [f"{graph.repository} announced on the DataHub home page"]

    @staticmethod
    def _post(graph: RunGraph) -> dict[str, JsonValue]:
        """State the home page card one repository's published graph is shown behind.

        The card is keyed by the repository it announces, so a later run rewrites that same one.
        """
        return {
            "urn": f"urn:li:post:mcmr-{graph.repository}",
            "postInfo": {
                "value": {
                    "type": "HOME_PAGE_ANNOUNCEMENT",
                    "content": {
                        "type": "LINK",
                        "title": f"MCMR: {graph.repository} code graph and enforcement history",
                        "description": (
                            f"{len(graph.datasets)} fact tables and {len(graph.jobs)} rule jobs "
                            f"MCMR published for {graph.repository}."
                        ),
                        "link": f"{_PAGE}/{flow_urn(graph.repository)}",
                    },
                    "created": 0,
                    "lastModified": 0,
                }
            },
        }
