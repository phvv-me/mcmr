import json
from datetime import UTC, datetime
from pathlib import Path

import anyio
import httpx
import pytest
from pydantic import JsonValue, TypeAdapter

from mcmr.commands.quality import history
from mcmr.plugins import HistoryContext, RuleTimeline, RunEvent, RunRecord, RunState
from mcmr_datahub import DataHubGraphQL, DataHubProvider, DataHubSettings
from mcmr_datahub.services.publication import dataset_urn, flow_urn, job_urn, subject_urn
from mcmr_datahub.services.recording import DataHubRecording

from ...support import needs_kernel, written

_PROJECT = """[tool.mcmr.execution]
external = true

[tool.mcmr.providers.datahub]
recorded = "recordings"
report_url = "https://example.invalid/run"
"""

_OBJECT = TypeAdapter(dict[str, JsonValue])

_SUBJECT = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.analytics.orders,PROD)"


def recorded(root: Path, assertions: list[JsonValue], keyed: JsonValue = None) -> Path:
    """Write one repository whose only recording answers the assertion history query."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    (recordings / "MCMRAssertionHistory.json").write_text(
        json.dumps(
            [
                {
                    "variables": {"urn": _SUBJECT} if keyed is None else keyed,
                    "response": {
                        "data": {
                            "dataset": {
                                "assertions": {
                                    "total": len(assertions),
                                    "assertions": assertions,
                                }
                            }
                        }
                    },
                }
            ]
        )
    )
    return written(root, {"pyproject.toml": _PROJECT})


def timelines(root: Path) -> list[RuleTimeline]:
    """Read the recorded history of the one asset these tests key their recording by."""
    return anyio.run(
        DataHubProvider().history,
        HistoryContext(
            repository=root,
            settings={"recorded": "recordings", "server": "http://recorded.invalid"},
            subjects=[_SUBJECT],
        ),
    )


def test_an_assertion_mcmr_never_wrote_is_not_read_as_one_of_its_timelines(
    tmp_path: Path,
) -> None:
    """Another tool's custom assertion names no rule, so it is skipped instead of guessed at."""
    foreign: JsonValue = {
        "urn": "urn:li:assertion:great-expectations-1",
        "info": {"description": "Row count is positive.", "externalUrl": ""},
        "runEvents": {
            "total": 1,
            "failed": 0,
            "succeeded": 1,
            "runEvents": [
                {
                    "timestampMillis": 1786096800000,
                    "status": "COMPLETE",
                    "result": {"type": "SUCCESS", "nativeResults": []},
                }
            ],
        },
    }

    assert timelines(recorded(tmp_path, [foreign])) == []


def test_a_run_event_without_a_verdict_or_a_moment_is_left_out_of_the_timeline(
    tmp_path: Path,
) -> None:
    """A partial event states nothing a later run can be compared against, so it is dropped."""
    partial: JsonValue = {
        "urn": "urn:li:assertion:mcmr-all-data0002-abc",
        "info": {"description": "ALL-DATA0002 Report an absent field.", "externalUrl": ""},
        "runEvents": {
            "total": 3,
            "failed": 1,
            "succeeded": 0,
            "runEvents": [
                {"timestampMillis": None, "status": "COMPLETE", "result": {"type": "FAILURE"}},
                {"timestampMillis": 1786096800000, "status": "COMPLETE", "result": {}},
                {
                    "timestampMillis": 1786096800000,
                    "status": "COMPLETE",
                    "result": {
                        "type": "FAILURE",
                        "nativeResults": [{"key": "rule", "value": "ALL-DATA0002"}],
                    },
                },
            ],
        },
    }

    found = timelines(recorded(tmp_path, [partial]))

    assert [(item.rule, len(item.events)) for item in found] == [("ALL-DATA0002", 1)]


def test_a_recorded_exchange_that_states_no_variables_object_answers_nothing(
    tmp_path: Path,
) -> None:
    """A recording keyed by something other than variables cannot answer a request by accident."""
    with pytest.raises(RuntimeError, match="holds no"):
        timelines(recorded(tmp_path, [], keyed="not an object"))


@needs_kernel
def test_history_says_so_when_no_previous_run_was_ever_recorded(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unrecorded asset is a plain answer rather than an empty table nobody can read."""
    history(recorded(tmp_path, []), assets=(_SUBJECT,))

    assert "No previous run was recorded" in capsys.readouterr().out


def test_every_published_entity_is_keyed_by_an_identity_a_later_run_lands_on() -> None:
    """Publication is an upsert, so the identity of each entity is derived and never generated.

    A fact table is named after the repository that owns it, a flow after the run, and a job after
    the rule, so a second run against the same repository rewrites the graph it already published
    instead of growing a second one beside it.
    """
    flow = "urn:li:dataFlow:(mcmr,chefe,PROD)"
    asset = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.analytics.orders,PROD)"

    assert dataset_urn("chefe/facts/call_fact") == (
        "urn:li:dataset:(urn:li:dataPlatform:mcmr,chefe/facts/call_fact,PROD)"
    )
    extraction = f"urn:li:dataJob:({flow},extract)"

    assert (flow_urn("chefe"), job_urn("chefe", job="extract")) == (flow, extraction)
    assert subject_urn(asset) == asset


def test_two_timelines_inside_one_fact_table_are_told_apart_by_the_file_each_names() -> None:
    """A fact table holds one timeline per reported file beside the repository-wide one."""
    moment = datetime(2026, 8, 7, 9, 34, tzinfo=UTC)
    stated = RunEvent(at=moment, state=RunState.FAILURE, properties={"rule": "ALL-DUPL0005"})
    whole = RuleTimeline(
        rule="ALL-DUPL0005",
        subject="demo/facts/literal_group_fact",
        events=[stated],
    )
    located = whole.model_copy(
        update={
            "events": [
                stated.model_copy(update={"properties": {"path": "src/orders.py"}}),
                stated.model_copy(update={"properties": {}}),
            ]
        }
    )

    assert (whole.where, located.where) == ("", "src/orders.py")


def opened(rule: str, *, path: str, urn: str) -> JsonValue:
    """Return one recorded assertion whose last run reported a rule failing at one file."""
    stated: list[JsonValue] = [
        {"key": "rule", "value": rule},
        {"key": "lane", "value": "deterministic"},
    ]
    if path:
        stated.append({"key": "path", "value": path})
    return {
        "urn": urn,
        "info": {"description": f"{rule} states something", "externalUrl": ""},
        "runEvents": {
            "total": 1,
            "failed": 1,
            "succeeded": 0,
            "runEvents": [
                {
                    "timestampMillis": 1786096800000,
                    "status": "COMPLETE",
                    "result": {"type": "FAILURE", "nativeResults": stated},
                }
            ],
        },
    }


def test_a_file_a_rule_stopped_reporting_is_closed_rather_than_left_failing() -> None:
    """A verdict about one file is written when a rule fails there and never written again.

    Nothing else would ever close it, so a repaired, renamed, or deleted file would read as
    failing forever. The rule that ran knows every file it still reports, and a rule that did not
    run closes nothing because silence is not a resolution.
    """
    held: list[JsonValue] = [
        opened("ALL-DUPL0005", path="kept.py", urn="urn:li:assertion:kept"),
        opened("ALL-DUPL0005", path="repaired.py", urn="urn:li:assertion:repaired"),
        opened("ALL-CALL0001", path="unrun.py", urn="urn:li:assertion:unrun"),
        opened("ALL-DUPL0005", path="", urn="urn:li:assertion:whole"),
    ]
    reported: list[JsonValue] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["operationName"] == "MCMRAssertionHistory":
            answer = {"dataset": {"assertions": {"total": len(held), "assertions": held}}}
            return httpx.Response(200, json={"data": answer})
        reported.append(payload["variables"])
        return httpx.Response(200, json={"data": {"reportAssertionResult": True}})

    async def reconcile() -> int:
        settings = DataHubSettings(server="https://catalog.example")
        async with DataHubGraphQL(settings, httpx.MockTransport(respond)) as gateway:
            return len(
                await DataHubRecording(gateway, "").reconcile(
                    ["demo/facts/literal_group_fact"],
                    [
                        RunRecord(rule="ALL-DUPL0005", subject="demo/facts/literal_group_fact"),
                        RunRecord(
                            rule="ALL-DUPL0005",
                            subject="demo/facts/literal_group_fact",
                            identity="kept.py demo",
                            path="kept.py",
                            state=RunState.FAILURE,
                        ),
                    ],
                )
            )

    assert anyio.run(reconcile) == 1
    closed = _OBJECT.validate_python(reported[0])
    assert closed["assertion"] == "urn:li:assertion:repaired"
    assert closed["type"] == "SUCCESS"
    assert closed["properties"] == [
        {"key": "rule", "value": "ALL-DUPL0005"},
        {"key": "lane", "value": "deterministic"},
        {"key": "path", "value": "repaired.py"},
        {"key": "resolution", "value": "no longer reported"},
    ]
