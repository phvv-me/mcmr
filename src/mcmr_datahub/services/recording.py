from datetime import UTC, datetime
from typing import TYPE_CHECKING

from anyio import sleep
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import RuleTimeline, RunEvent, RunRecord, RunState

from .assertions import DataHubAssertionQueries
from .publication.labels import assertion_urn, subject_urn
from .publication.reported import ReportedFiles
from .transport.exceptions import DataHubRequestError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .transport.graphql import DataHubGraphQL

# What DataHub calls the assertions this tool reports, which is the category shown beside them.
_CATEGORY = "MCMR"

# The data platform DataHub attributes these assertions to, so they are attributable to a tool.
_PLATFORM = "mcmr"

_WINDOW = 50

_SETTLING = (0.25, 0.5, 1.0, 2.0)

# What each recorded verdict is called in the DataHub assertion result contract.
_RESULT = {
    RunState.SUCCESS: "SUCCESS",
    RunState.FAILURE: "FAILURE",
    RunState.ERROR: "ERROR",
}
_STATE = {name: state for state, name in _RESULT.items()}

_RESOLVED = "no longer reported"


class DataHubRecording:
    """Record and read what one MCMR run concluded, in the two shapes DataHub already keeps.

    A custom assertion is DataHub's own model for a check some external tool owns, so a run leaves
    a timeline the catalog already knows how to show and query rather than a document only MCMR
    can read. The assertion identity is derived from the rule and the asset, which is what makes a
    later run land on the same assertion instead of creating a second one. Beside that machine
    timeline each judged asset receives one institutional memory link, which is the receipt a
    person opening the asset reads.
    """

    def __init__(self, gateway: DataHubGraphQL, report_url: str, *, run: str = "") -> None:
        self.gateway = gateway
        self.report_url = report_url
        self.run = run

    async def declare(self, record: RunRecord) -> str:
        """Upsert the assertion one verdict belongs to and return its identity."""
        assertion = assertion_urn(record)
        await self.gateway.execute(
            DataHubAssertionQueries.upsert,
            {
                "assertion": assertion,
                "entity": subject_urn(record.subject),
                "category": _CATEGORY,
                "description": f"{record.rule} {record.summary}".strip(),
                "platform": _PLATFORM,
                "externalUrl": self.report_url or None,
            },
            "MCMRUpsertAssertion",
        )
        return assertion

    async def read(self, subject: str) -> list[RuleTimeline]:
        """Return every MCMR timeline DataHub already holds for one governed asset."""
        urn = subject_urn(subject)
        data = await self.gateway.execute(
            DataHubAssertionQueries.timeline,
            {"urn": urn, "count": _WINDOW},
            "MCMRAssertionHistory",
        )
        dataset = self._optional(self._mapping(data), "dataset")
        held = self._optional(dataset, "assertions")
        return [
            timeline
            for value in self._optional_sequence(held, "assertions")
            if (timeline := self._timeline(urn, self._mapping(value))) is not None
        ]

    async def receipt(self, subject: str, records: Sequence[RunRecord], *, label: str) -> str:
        """Leave the human receipt on one judged subject and state what this run concluded."""
        await self.remember(subject, label=label)
        stated = [record for record in records if record.subject == subject]
        failing = sum(record.state is RunState.FAILURE for record in stated)
        linked = f"linked {self.report_url}" if self.report_url else "with no report to link"
        return (
            f"{subject} {len(stated)} verdicts recorded "
            f"({len(stated) - failing} passing, {failing} failing), {linked}"
        )

    async def reconcile(
        self,
        subjects: Sequence[str],
        records: Sequence[RunRecord],
        *,
        repository: str = "",
        at: datetime | None = None,
    ) -> list[str]:
        """Close every file-scoped verdict this run no longer reports, and say how many.

        A verdict about one file is written when a rule fails there, and nothing writes it again
        once the file is repaired, renamed, or deleted, so it would read as failing forever. A
        rule that ran this run knows every file it still reports, which is what licenses closing
        the rest. A rule that did not run closes nothing, because silence is not a resolution.
        """
        reported = ReportedFiles.of(records)
        held = [found for subject in subjects for found in await self.reported(subject)]
        closed = [found for found in held if reported.settled(rule=found[1], path=found[2])]
        moment = at or datetime.now(UTC)
        for assertion, rule, path, lane in closed:
            await self.report_result(
                self._resolution(assertion, rule=rule, path=path, lane=lane, at=moment)
            )
        return [f"{repository} closed {len(closed)} file verdicts".strip()] if closed else []

    async def record(self, records: Sequence[RunRecord], at: datetime | None = None) -> int:
        """Declare every assertion this run reached, then report each verdict against it.

        DataHub resolves an assertion through an index its own upsert reaches seconds later, so
        reporting a result in the same breath as the upsert that created it pays that whole wait
        once per assertion. Declaring the run's assertions first spends that window on the rest of
        the batch instead, which is the difference between a run that records in seconds and one
        that spends minutes asleep.

        Every result also states the identity of the invocation that reached it, so a reader who
        opened one rule's timeline can ask what else the same run concluded.
        """
        declared = [(record, await self.declare(record)) for record in records]
        moment = at or datetime.now(UTC)
        for record, assertion in declared:
            stated = record.properties | ({"runId": self.run} if self.run else {})
            await self.report_result(
                {
                    "assertion": assertion,
                    "timestampMillis": int(moment.timestamp() * 1000),
                    "type": _RESULT[record.state],
                    "properties": [{"key": key, "value": value} for key, value in stated.items()],
                    "externalUrl": self.report_url or None,
                }
            )
        return len(declared)

    async def remember(self, subject: str, *, label: str) -> None:
        """Point one judged asset at the run that judged it, without overwriting anything.

        Institutional memory is additive and editable, so a link states what a tool found beside
        whatever a person wrote. `updateDescription` would replace that sentence instead, which is
        why an agent must never reach for it. `addLink` refuses a link an asset already holds, so
        the link this run wants is read first and only the missing one is written, which is what
        makes a second run against the same asset land instead of failing.
        """
        if not self.report_url or await self.remembered(subject, label=label):
            return
        await self.gateway.execute(
            DataHubAssertionQueries.link,
            {"urn": subject_urn(subject), "url": self.report_url, "label": label},
            "MCMRWriteback",
        )

    async def remembered(self, subject: str, *, label: str) -> bool:
        """Whether one judged asset already points at this run report under this label."""
        data = await self.gateway.execute(
            DataHubAssertionQueries.links,
            {"urn": subject_urn(subject)},
            "MCMRWritebackLinks",
        )
        dataset = self._optional(self._mapping(data), "dataset")
        memory = self._optional(dataset, "institutionalMemory")
        return any(
            self._text(element.get("url")) == self.report_url
            and self._text(element.get("label")) == label
            for value in self._optional_sequence(memory, "elements")
            if (element := self._mapping(value))
        )

    async def report_result(self, variables: dict[str, JsonValue]) -> None:
        """Report one verdict, waiting out the window a newly created assertion is unresolvable in.

        DataHub answers `reportAssertionResult` by resolving the asserted entity through an index
        its own `upsertCustomAssertion` reaches about a second later, so the first result against a
        brand new assertion is rejected until that write settles. Each attempt after the last delay
        raises whatever the server actually said, so a request that is wrong rather than early
        still fails with the server's own error.
        """
        for delay in _SETTLING:
            try:
                await self.gateway.execute(
                    DataHubAssertionQueries.report, variables, "MCMRReportAssertionResult"
                )
            except DataHubRequestError:
                await sleep(delay)
            else:
                return
        await self.gateway.execute(
            DataHubAssertionQueries.report, variables, "MCMRReportAssertionResult"
        )

    async def reported(self, subject: str) -> list[tuple[str, str, str, str]]:
        """Return every file-scoped verdict one subject still holds open, as identity and place."""
        data = await self.gateway.execute(
            DataHubAssertionQueries.timeline,
            {"urn": subject_urn(subject), "count": _WINDOW},
            "MCMRAssertionHistory",
        )
        dataset = self._optional(self._mapping(data), "dataset")
        held = self._optional(dataset, "assertions")
        return [
            found
            for value in self._optional_sequence(held, "assertions")
            if (found := self._open(self._mapping(value))) is not None
        ]

    @staticmethod
    def _mapping(value: JsonValue) -> dict[str, JsonValue]:
        """Validate one required GraphQL object."""
        return TypeAdapter(dict[str, JsonValue]).validate_python(value)

    @staticmethod
    def _sequence(value: JsonValue) -> list[JsonValue]:
        """Validate one required GraphQL list."""
        return TypeAdapter(list[JsonValue]).validate_python(value)

    @staticmethod
    def _text(value: JsonValue | None) -> str:
        """Read nullable GraphQL text without inventing metadata."""
        return value if isinstance(value, str) else ""

    @classmethod
    def _optional(cls, parent: Mapping[str, JsonValue], key: str) -> dict[str, JsonValue]:
        """Validate one nullable GraphQL object as an empty mapping when absent."""
        return {} if parent.get(key) is None else cls._mapping(parent[key])

    @classmethod
    def _optional_sequence(cls, parent: Mapping[str, JsonValue], key: str) -> list[JsonValue]:
        """Validate one nullable GraphQL list as an empty list when absent.

        A verdict reported without properties comes back with an explicit `null` under
        `nativeResults`, so a selected key is present while its value is not a list.
        """
        return [] if parent.get(key) is None else cls._sequence(parent[key])

    def _event(self, value: JsonValue) -> RunEvent | None:
        """Project one recorded assertion run into the verdict it states."""
        event = self._mapping(value)
        result = self._optional(event, "result")
        state = _STATE.get(self._text(result.get("type")))
        moment = event.get("timestampMillis")
        if state is None or not isinstance(moment, int):
            return None
        return RunEvent(
            at=datetime.fromtimestamp(moment / 1000, UTC),
            state=state,
            properties=self._properties(result),
        )

    def _events(self, assertion: Mapping[str, JsonValue]) -> list[RunEvent]:
        """Return every recorded run of one assertion, oldest first."""
        runs = self._optional(assertion, "runEvents")
        found = [
            event
            for value in self._optional_sequence(runs, "runEvents")
            if (event := self._event(value)) is not None
        ]
        return sorted(found, key=lambda item: item.at)

    def _open(self, assertion: Mapping[str, JsonValue]) -> tuple[str, str, str, str] | None:
        """Project one assertion into the file it still reports, or skip one that reports none."""
        events = self._events(assertion)
        if not events or events[-1].state is not RunState.FAILURE:
            return None
        stated = events[-1].properties
        rule, path = stated.get("rule", ""), stated.get("path", "")
        found = (self._text(assertion.get("urn")), rule, path, stated.get("lane", ""))
        return found if rule and path else None

    def _properties(self, result: Mapping[str, JsonValue]) -> dict[str, str]:
        """Return the flat properties one recorded verdict carried."""
        return {
            self._text(entry.get("key")): self._text(entry.get("value"))
            for value in self._optional_sequence(result, "nativeResults")
            if (entry := self._mapping(value))
        }

    def _resolution(
        self,
        assertion: str,
        *,
        rule: str,
        path: str,
        lane: str,
        at: datetime,
    ) -> dict[str, JsonValue]:
        """State that one file a rule used to report is not reported by this run."""
        stated: list[JsonValue] = [
            {"key": "rule", "value": rule},
            {"key": "path", "value": path},
            {"key": "resolution", "value": _RESOLVED},
        ]
        if lane:
            stated.insert(1, {"key": "lane", "value": lane})
        return {
            "assertion": assertion,
            "timestampMillis": int(at.timestamp() * 1000),
            "type": _RESULT[RunState.SUCCESS],
            "properties": stated,
            "externalUrl": self.report_url or None,
        }

    def _timeline(self, subject: str, assertion: Mapping[str, JsonValue]) -> RuleTimeline | None:
        """Project one DataHub assertion into its rule timeline, or skip one MCMR never wrote."""
        events = self._events(assertion)
        rule = next((event.properties.get("rule", "") for event in reversed(events)), "")
        if not rule:
            return None
        described = self._text(self._optional(assertion, "info").get("description"))
        return RuleTimeline(
            rule=rule,
            subject=subject,
            summary=described.removeprefix(rule).strip(),
            events=events,
        )
