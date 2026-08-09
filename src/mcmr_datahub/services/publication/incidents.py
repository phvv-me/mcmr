from typing import TYPE_CHECKING

from pydantic import JsonValue, TypeAdapter

from ..transport.graphql import DataHubGraphQL
from ..transport.openapi import DataHubOpenAPI
from .flapping import FlapDetector
from .labels import dataset_urn, table_terms, valued
from .reported import ReportedFiles

if TYPE_CHECKING:
    from collections.abc import Container, Mapping, Sequence

    import httpx

    from mcmr.plugins import RuleTimeline, RunGraph, RunRecord

    from ..configuration import DataHubSettings
    from .history import SubjectHistory

# How many incidents one fact table is read for, which bounds the idempotency check.
_WINDOW = 50

# What MCMR calls this kind of incident, which is the label an incident list is scanned by.
_CUSTOM = "Intermittent finding"

# How loudly an on and off subject asks for attention, which is beneath a table that is simply
# broken and above one that is merely untidy.
_PRIORITY = "MEDIUM"


class DataHubIncidents:
    """Raise and close the incident an intermittently failing subject deserves.

    An assertion timeline is where a verdict lives, and reading one is how a person notices that a
    rule keeps changing its mind. Nobody reads fifty of them. An incident is the entity DataHub
    already raises the health of a dataset with, so the tables whose verdicts will not settle
    surface on their own rather than waiting for somebody to scroll. The incident is recognized by
    the title its rule and file always produce, which is what keeps a second run from raising a
    duplicate beside the one it already opened.
    """

    active = """query MCMRActiveIncidents($urn: String!, $count: Int!) {
  dataset(urn: $urn) {
    incidents(state: ACTIVE, start: 0, count: $count) {
      total
      incidents {
        urn
        title
        status { state }
      }
    }
  }
}"""

    raised = """mutation MCMRRaiseIncident(
  $customType: String!
  $title: String!
  $description: String!
  $resourceUrn: String!
  $priority: IncidentPriority!
) {
  raiseIncident(
    input: {
      type: CUSTOM
      customType: $customType
      title: $title
      description: $description
      resourceUrn: $resourceUrn
      priority: $priority
      status: {state: ACTIVE, stage: TRIAGE}
      source: {type: MANUAL}
    }
  )
}"""

    resolved = """mutation MCMRResolveIncident($urn: String!, $message: String!) {
  updateIncidentStatus(urn: $urn, input: {state: RESOLVED, stage: FIXED, message: $message})
}"""

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def reconcile(
        self,
        graph: RunGraph,
        timelines: Sequence[RuleTimeline],
        records: Sequence[RunRecord] = (),
        *,
        run: str,
    ) -> list[str]:
        """Open an incident for every subject that alternates and close every one that settled.

        Whether a subject is still failing is read from what this run itself concluded rather than
        from the timeline, because a verdict closed moments ago has not reached the index a read
        goes through, and an incident that outlives its own repair by a whole run is noise.

        Every fact table also records how much its noisiest subject moved, so a reader can sort
        for the tables whose verdicts will not settle before any of them is bad enough to raise.
        """
        published = [dataset_urn(dataset.name) for dataset in graph.datasets]
        if not published:
            return []
        detector = FlapDetector(timelines, published, ReportedFiles.of(records))
        histories = detector.histories()
        async with DataHubGraphQL(self.settings, self.transport) as gateway:
            open_incidents = {
                urn: await self._open(gateway, urn)
                for urn in sorted({history.subject for history in histories})
            }
            opened = await self._raise(gateway, histories, held=open_incidents)
            closed = await self._close(gateway, histories, held=open_incidents, run=run)
        await self._score(graph, detector.scores(), flapping=self._flapping(histories))
        return self._stated(graph.repository, opened=opened, closed=closed)

    @staticmethod
    def _flapping(histories: Sequence[SubjectHistory]) -> set[str]:
        """Return every fact table currently reporting a subject that will not settle."""
        return {history.subject for history in histories if history.alternates and history.failing}

    @staticmethod
    def _mapping(value: JsonValue) -> dict[str, JsonValue]:
        """Validate one required GraphQL object."""
        return TypeAdapter(dict[str, JsonValue]).validate_python(value)

    @staticmethod
    def _stated(repository: str, *, opened: int, closed: int) -> list[str]:
        """Say what changed, and say nothing at all when nothing did."""
        if not opened and not closed:
            return []
        return [
            f"{repository} raised {opened} intermittent findings and resolved {closed}".strip()
        ]

    @classmethod
    def _optional(cls, parent: Mapping[str, JsonValue], key: str) -> dict[str, JsonValue]:
        """Validate one nullable GraphQL object as an empty mapping when absent."""
        return {} if parent.get(key) is None else cls._mapping(parent[key])

    async def _close(
        self,
        gateway: DataHubGraphQL,
        histories: Sequence[SubjectHistory],
        *,
        held: Mapping[str, Mapping[str, str]],
        run: str,
    ) -> int:
        """Close every open incident whose subject now reads passing, naming the run that did."""
        settled = [history for history in histories if not history.failing]
        closed = 0
        for history in settled:
            incident = held.get(history.subject, {}).get(history.title, "")
            if incident:
                await gateway.execute(
                    self.resolved,
                    {"urn": incident, "message": history.resolution(run)},
                    "MCMRResolveIncident",
                )
                closed += 1
        return closed

    async def _open(self, gateway: DataHubGraphQL, subject: str) -> dict[str, str]:
        """Return the incidents one fact table already holds open, by the title each states."""
        data = await gateway.execute(
            self.active,
            {"urn": subject, "count": _WINDOW},
            "MCMRActiveIncidents",
        )
        dataset = self._optional(self._mapping(data), "dataset")
        found = self._optional(dataset, "incidents").get("incidents")
        return self._titles(found if isinstance(found, list) else [])

    async def _raise(
        self,
        gateway: DataHubGraphQL,
        histories: Sequence[SubjectHistory],
        *,
        held: Mapping[str, Mapping[str, str]],
    ) -> int:
        """Raise one incident per alternating subject that is failing and has none open."""
        wanted = [
            history
            for history in histories
            if history.alternates and history.failing
            if history.title not in held.get(history.subject, {})
        ]
        for history in wanted:
            await gateway.execute(
                self.raised,
                {
                    "customType": _CUSTOM,
                    "title": history.title,
                    "description": history.description,
                    "resourceUrn": history.subject,
                    "priority": _PRIORITY,
                },
                "MCMRRaiseIncident",
            )
        return len(wanted)

    async def _score(
        self,
        graph: RunGraph,
        scores: Mapping[str, int],
        *,
        flapping: Container[str],
    ) -> None:
        """Record on every published fact table how much its noisiest subject moves."""
        published = [dataset_urn(dataset.name) for dataset in graph.datasets]
        entities: list[JsonValue] = [
            {
                "urn": urn,
                **valued({"flapScore": str(scores.get(urn, 0))}),
                **table_terms(flapping=urn in flapping),
            }
            for urn in published
        ]
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            await openapi.ingest("dataset", entities)

    def _titles(self, incidents: Sequence[JsonValue]) -> dict[str, str]:
        """Return where each open incident lives, keyed by the title it is recognized by."""
        found: dict[str, str] = {}
        for value in incidents:
            incident = self._mapping(value)
            state = self._optional(incident, "status").get("state")
            title, urn = incident.get("title"), incident.get("urn")
            if state == "ACTIVE" and isinstance(title, str) and isinstance(urn, str):
                found.setdefault(title, urn)
        return found
