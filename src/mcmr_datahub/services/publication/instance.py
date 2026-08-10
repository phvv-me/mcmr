from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ..transport.openapi import DataHubOpenAPI
from .directory import DataHubDirectory
from .labels import flow_urn, instance_urn, labelled

if TYPE_CHECKING:
    import httpx
    from pydantic import JsonValue

    from mcmr.plugins import RunGraph, RunSummary

    from ..configuration import DataHubSettings

_KIND = "BATCH_AD_HOC"

# What DataHub is told produced this result, beside its own success or failure vocabulary.
_NATIVE = "mcmr"

# The two states one recorded run passes through, which is what puts it on the flow's Runs tab.
_STARTED = "STARTED"
_COMPLETE = "COMPLETE"

_SUCCESS = "SUCCESS"


class DataHubRunInstance:
    """Record one whole MCMR invocation as the run DataHub already shows beneath a flow.

    An assertion timeline answers what one rule keeps concluding. It cannot answer what a single
    invocation did, because every verdict in it belongs to a different rule and a different day.
    A process instance is the entity DataHub already has for that question, so the flow a
    repository publishes gains a run history rather than a second document nobody looks for. The
    instance is keyed by the identity every verdict of the same run was stamped with, which is
    what lets a reader pivot from one rule's timeline straight to the run that wrote it.
    """

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def publish(
        self,
        graph: RunGraph,
        summary: RunSummary,
        *,
        run: str,
        at: datetime | None = None,
    ) -> list[str]:
        """Write one run, the flow it belongs to, and the two events that bound it.

        A run instance with no flow above it is unreachable, so a run that published no fact
        table records nothing rather than an orphan the catalog cannot show.
        """
        if not run or not graph.datasets:
            return []
        completed = at or datetime.now(UTC)
        started = completed - timedelta(milliseconds=summary.duration_milliseconds)
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            await openapi.ingest(
                "dataprocessinstance",
                [self._started(graph, summary, run=run, at=started)],
            )
            await openapi.ingest(
                "dataprocessinstance",
                [self._completed(summary, run=run, at=completed)],
            )
        seconds = summary.duration_milliseconds / 1000
        spent = summary.spend.tokens
        return [
            f"{graph.repository} recorded run {run}, "
            f"{summary.rules.executed} rules and {summary.failures} failures in {seconds:.1f}s"
            + (f" for {spent} tokens" if spent else "")
        ]

    @staticmethod
    def _moment(at: datetime) -> int:
        """Return the millisecond stamp every DataHub timeseries event is keyed by."""
        return int(at.timestamp() * 1000)

    @staticmethod
    def _properties(graph: RunGraph, summary: RunSummary, *, run: str) -> dict[str, str]:
        """Return how much this run reached and what kind of rules reached it."""
        return {"runId": run, "repository": graph.repository} | summary.properties

    def _completed(self, summary: RunSummary, *, run: str, at: datetime) -> dict[str, JsonValue]:
        """State that the invocation completed successfully."""
        result: dict[str, JsonValue] = {
            "type": _SUCCESS,
            "nativeResultType": _NATIVE,
        }
        return {
            "urn": instance_urn(run),
            "dataProcessInstanceRunEvent": {
                "value": {
                    "timestampMillis": self._moment(at),
                    "status": _COMPLETE,
                    "attempt": 1,
                    "durationMillis": round(summary.duration_milliseconds),
                    "result": result,
                }
            },
        }

    def _started(
        self,
        graph: RunGraph,
        summary: RunSummary,
        *,
        run: str,
        at: datetime,
    ) -> dict[str, JsonValue]:
        """State the run itself, the flow it ran under, and everything it reached."""
        moment = self._moment(at)
        properties: dict[str, JsonValue] = {
            name: value for name, value in self._properties(graph, summary, run=run).items()
        }
        stated: dict[str, JsonValue] = {
            "name": run,
            "type": _KIND,
            "created": {
                "time": moment,
                "actor": DataHubDirectory(
                    self.settings.writeback.people,
                    self.settings.writeback.owner,
                    graph.spent,
                ).actor,
            },
            "customProperties": properties,
        }
        report = self.settings.report
        relationships: dict[str, JsonValue] = {
            "parentTemplate": flow_urn(graph.repository),
            "upstreamInstances": [],
        }
        return {
            "urn": instance_urn(run),
            "dataProcessInstanceProperties": {
                "value": stated | ({"externalUrl": report} if report else {})
            },
            "dataProcessInstanceRelationships": {"value": relationships},
            "dataProcessInstanceRunEvent": {
                "value": {"timestampMillis": moment, "status": _STARTED, "attempt": 1}
            },
            **labelled("run"),
        }
