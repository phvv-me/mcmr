import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
from pydantic import JsonValue, TypeAdapter

from mcmr.plugins import RuleTimeline, RunEvent, RunGraph, RunRecord, RunState
from mcmr_datahub import DataHubIncidents, DataHubSettings, FlapDetector
from mcmr_datahub.services.publication import dataset_urn, word_urn

from ..support import aspect, run_graph, table

if TYPE_CHECKING:
    from collections.abc import Sequence

_TABLE = dataset_urn(table())

_GRAPH = run_graph()

_ENTITIES = TypeAdapter(list[dict[str, JsonValue]])

_ALTERNATING = (RunState.FAILURE, RunState.SUCCESS, RunState.FAILURE)


def timeline(
    states: Sequence[RunState] = _ALTERNATING,
    *,
    rule: str = "ALL-DUPL0005",
    where: str = "src/orders.py",
    subject: str = _TABLE,
) -> RuleTimeline:
    """Return one recorded timeline whose verdicts pass through the stated states in order."""
    moment = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    return RuleTimeline(
        rule=rule,
        subject=subject,
        events=[
            RunEvent(
                at=moment.replace(hour=9 + item),
                state=state,
                properties={"rule": rule, "path": where},
            )
            for item, state in enumerate(states)
        ],
    )


def reconciled(
    timelines: Sequence[RuleTimeline],
    *,
    records: Sequence[RunRecord] = (),
    open_incidents: Sequence[JsonValue] = (),
    graph: RunGraph = _GRAPH,
    run: str = "mcmr-chefe-1786096800000",
) -> tuple[dict[str, list[JsonValue]], list[dict[str, JsonValue]], list[str]]:
    """Reconcile incidents through a mock transport and return what was asked and ingested."""
    asked: dict[str, list[JsonValue]] = {}
    posted: list[dict[str, JsonValue]] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        if not request.url.path.endswith("/api/graphql"):
            posted.extend(_ENTITIES.validate_python(json.loads(request.content)))
            return httpx.Response(200, json=[])
        payload = json.loads(request.content)
        asked.setdefault(payload["operationName"], []).append(payload["variables"])
        if payload["operationName"] == "MCMRActiveIncidents":
            held = {"incidents": {"total": 0, "incidents": list(open_incidents)}}
            return httpx.Response(200, json={"data": {"dataset": held}})
        return httpx.Response(200, json={"data": {"raiseIncident": "urn:li:incident:new"}})

    async def publish() -> list[str]:
        settings = DataHubSettings(server="https://catalog.example")
        return await DataHubIncidents(settings, httpx.MockTransport(respond)).reconcile(
            graph,
            list(timelines),
            list(records),
            run=run,
        )

    return asked, posted, anyio.run(publish)


def active(title: str, *, urn: str = "urn:li:incident:held") -> JsonValue:
    """Return one incident a fact table already holds open under the stated title."""
    return {"urn": urn, "title": title, "status": {"state": "ACTIVE"}}


def test_a_subject_that_fails_passes_and_fails_again_raises_one_incident() -> None:
    """A rule that keeps changing its mind is a different problem from one that keeps failing."""
    asked, _, receipts = reconciled([timeline()])
    raised = asked["MCMRRaiseIncident"][0]

    assert isinstance(raised, dict)
    assert raised["title"] == "ALL-DUPL0005 is intermittent at src/orders.py"
    assert raised["resourceUrn"] == _TABLE
    assert raised["priority"] == "MEDIUM"
    assert raised["customType"] == "Intermittent finding"
    assert "failing on 2026-08-07 0900, then passing on 2026-08-07 1000" in str(
        raised["description"]
    )
    assert "changing verdict 2 times" in str(raised["description"])
    assert receipts == ["chefe raised 1 intermittent findings and resolved 0"]


def test_an_incident_already_open_for_the_same_subject_is_never_raised_twice() -> None:
    """The title one rule and file always produce is what a second run recognizes them by."""
    held = [active("ALL-DUPL0005 is intermittent at src/orders.py")]

    asked, _, receipts = reconciled([timeline()], open_incidents=held)

    assert "MCMRRaiseIncident" not in asked
    assert receipts == []


def test_a_subject_that_settled_closes_the_incident_and_names_the_run_that_did() -> None:
    """An incident nobody closes is noise, so the run that steadied the subject closes it."""
    steady = (*_ALTERNATING, RunState.SUCCESS)
    held = [active("ALL-DUPL0005 is intermittent at src/orders.py")]

    asked, _, receipts = reconciled([timeline(steady)], open_incidents=held)
    resolved = asked["MCMRResolveIncident"][0]

    assert isinstance(resolved, dict)
    assert resolved["urn"] == "urn:li:incident:held"
    assert resolved["message"] == (
        "Run mcmr-chefe-1786096800000 recorded ALL-DUPL0005 passing at src/orders.py, so the off "
        "and on pattern this incident was raised for has stopped."
    )
    assert "MCMRRaiseIncident" not in asked
    assert receipts == ["chefe raised 0 intermittent findings and resolved 1"]


def test_the_run_that_repaired_a_subject_is_the_run_that_closes_its_incident() -> None:
    """A verdict closed moments ago is not in the index a read goes through, so the run says so.

    Reading the timeline back would still show the file failing, and the incident would outlive
    its own repair by a whole run, which is exactly the noise an incident is meant to replace.
    """
    held = [active("ALL-DUPL0005 is intermittent at src/orders.py")]
    ran = [RunRecord(rule="ALL-DUPL0005", subject=_TABLE)]

    asked, posted, receipts = reconciled([timeline()], records=ran, open_incidents=held)

    assert asked["MCMRResolveIncident"]
    assert "MCMRRaiseIncident" not in asked
    assert receipts == ["chefe raised 0 intermittent findings and resolved 1"]
    assert aspect(posted[0], "glossaryTerms")["terms"] == [
        {"urn": word_urn("fact table")},
        {"urn": word_urn("verdict")},
    ]


def test_a_rule_that_did_not_run_settles_nothing_it_used_to_report() -> None:
    """Silence is not a resolution, so a rule nobody selected leaves its incident where it is."""
    held = [active("ALL-DUPL0005 is intermittent at src/orders.py")]
    elsewhere = [RunRecord(rule="ALL-CALL0001", subject=_TABLE)]

    asked, _, receipts = reconciled([timeline()], records=elsewhere, open_incidents=held)

    assert "MCMRResolveIncident" not in asked and receipts == []


def test_a_subject_that_settled_with_no_incident_open_closes_nothing() -> None:
    """Closing what was never opened would be a second write nobody asked for."""
    asked, _, receipts = reconciled([timeline((RunState.SUCCESS,))])

    assert "MCMRResolveIncident" not in asked and "MCMRRaiseIncident" not in asked
    assert receipts == []


def test_a_subject_that_only_ever_failed_raises_nothing() -> None:
    """A rule failing every run is already visible, so nothing new is said about it."""
    asked, _, _ = reconciled([timeline((RunState.FAILURE, RunState.FAILURE))])

    assert "MCMRRaiseIncident" not in asked


def test_every_fact_table_records_how_much_its_noisiest_subject_moves() -> None:
    """Sorting by how unsteady a table is comes before any of it is bad enough to raise."""
    quiet = timeline((RunState.FAILURE,), rule="ALL-CALL0001", where="src/quiet.py")

    _, posted, _ = reconciled([timeline(), quiet])
    stated = aspect(posted[0], "structuredProperties")["properties"]
    terms = aspect(posted[0], "glossaryTerms")["terms"]

    assert stated == [
        {"propertyUrn": "urn:li:structuredProperty:mcmr.flapScore", "values": [{"double": 2.0}]}
    ]
    assert terms == [
        {"urn": word_urn("fact table")},
        {"urn": word_urn("verdict")},
        {"urn": word_urn("intermittent finding")},
    ]


def test_a_steady_fact_table_is_never_called_intermittent() -> None:
    """The term is only worth attaching while it is true, so a settled table drops it."""
    _, posted, _ = reconciled([timeline((RunState.SUCCESS,))])
    terms = aspect(posted[0], "glossaryTerms")["terms"]

    assert terms == [{"urn": word_urn("fact table")}, {"urn": word_urn("verdict")}]
    assert aspect(posted[0], "structuredProperties")["properties"] == [
        {"propertyUrn": "urn:li:structuredProperty:mcmr.flapScore", "values": [{"double": 0.0}]}
    ]


def test_nothing_is_raised_against_a_table_this_writeback_did_not_publish() -> None:
    """Raising against an unpublished entity materializes a stub, so it is simply never done."""
    elsewhere = timeline(subject=dataset_urn("other/facts/literal_group_fact"))

    asked, _, receipts = reconciled([elsewhere])

    assert "MCMRActiveIncidents" not in asked and receipts == []
    assert reconciled([timeline()], graph=RunGraph(repository="chefe")) == ({}, [], [])


def test_a_verdict_about_the_whole_table_is_not_a_subject_that_can_flap() -> None:
    """A rule with no file to point at is the table's own state rather than a place inside it."""
    whole = timeline(where="")

    asked, _, _ = reconciled([whole])

    assert "MCMRRaiseIncident" not in asked


def test_an_incident_a_reader_already_resolved_is_not_read_as_open() -> None:
    """Only what DataHub still calls active can stop this run from raising its own."""
    held: list[JsonValue] = [
        {"urn": "urn:li:incident:done", "title": "ALL-DUPL0005 is intermittent at src/orders.py"},
        {
            "title": "ALL-DUPL0005 is intermittent at src/orders.py",
            "status": {"state": "RESOLVED"},
        },
    ]

    asked, _, _ = reconciled([timeline()], open_incidents=held)

    assert "MCMRRaiseIncident" in asked


def test_an_unanswered_verdict_reads_as_unanswered_rather_than_as_a_failure() -> None:
    """A rule that could not answer said nothing about the file, and the timeline says so."""
    states = (RunState.FAILURE, RunState.SUCCESS, RunState.FAILURE, RunState.ERROR)

    detector = FlapDetector([timeline(states)], [_TABLE])
    history = detector.histories()[0]

    assert history.timeline[-1] == "unanswered on 2026-08-07 1200"
    assert (history.changes, history.alternates, history.failing) == (3, True, False)
