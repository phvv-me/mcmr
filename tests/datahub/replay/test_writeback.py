import json
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import httpx
import pytest

from mcmr.commands.interface import RepairMode
from mcmr.commands.quality import RunPublication, check, identity
from mcmr.domain.contracts import Finding
from mcmr.facts import SourceSpan
from mcmr.plugins import (
    HistoryContext,
    PublicationContext,
    RepairState,
    RunRecord,
    RunState,
)
from mcmr.presentation.reports import CheckReport, RuleFailure, RulePass
from mcmr_datahub import (
    DataHubGraphQL,
    DataHubProvider,
    DataHubRequestError,
    DataHubSettings,
)
from mcmr_datahub.services import recording as recording_module
from mcmr_datahub.services.publication import assertion_urn
from mcmr_datahub.services.recording import DataHubRecording

from ...support import needs_kernel, project_root, written

if TYPE_CHECKING:
    from pydantic import JsonValue

_EXAMPLE = project_root() / "examples" / "datahub"


type Responder = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]


async def noop(seconds: float) -> None:
    """Stand in for the settling wait so a retry test costs no wall time."""


_PROJECT = """[tool.mcmr.execution]
external = true

[tool.mcmr.providers.datahub]
recorded = "recordings"
report_url = "https://example.invalid/run"
page_size = 10
max_assets = 10
"""

_GOVERNED = {
    "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.marts.clean,PROD)",
    "properties": {"description": "Everything this asset needs.", "lastModified": {"time": 0}},
    "deprecation": None,
    "ownership": {"owners": [{"owner": {"urn": "urn:li:corpGroup:data", "name": "data"}}]},
    "domain": {"domain": {"urn": "urn:li:domain:sales", "properties": {"name": "Sales"}}},
    "schemaMetadata": {
        "fields": [
            {
                "fieldPath": "id",
                "type": "NUMBER",
                "description": "Row identifier.",
                "globalTags": None,
                "glossaryTerms": None,
            }
        ]
    },
}


def clean(root: Path) -> Path:
    """Write one repository whose recorded catalog leaves nothing for a rule to report."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    (recordings / "MCMRDataAssets.json").write_text(
        json.dumps(
            [
                {
                    "variables": {"query": "*", "count": 10, "start": 0},
                    "response": {
                        "data": {
                            "searchAcrossEntities": {
                                "total": 1,
                                "searchResults": [{"entity": _GOVERNED}],
                            }
                        }
                    },
                }
            ]
        )
    )
    for operation, answer in (
        ("MCMRFieldLineage", {"dataset": {"urn": _GOVERNED["urn"], "fineGrainedLineages": []}}),
        ("MCMRDataLineage", {"searchAcrossLineage": {"total": 0, "searchResults": []}}),
    ):
        variables = {"urn": _GOVERNED["urn"]}
        if operation == "MCMRDataLineage":
            variables = variables | {"count": 10, "start": 0}
        (recordings / f"{operation}.json").write_text(
            json.dumps([{"variables": variables, "response": {"data": answer}}])
        )
    for captured in _EXAMPLE.glob("recordings/*.json"):
        if captured.name not in {item.name for item in recordings.glob("*.json")}:
            (recordings / captured.name).write_text(captured.read_text())
    return written(
        root,
        {
            "pyproject.toml": _PROJECT,
            "rollup.py": '"""A rollup naming nothing the catalog governs."""\n\nTOTAL = 1\n',
        },
    )


def example(root: Path) -> Path:
    """Copy the recorded example into one writable directory a check may repair."""
    for source in _EXAMPLE.rglob("*"):
        target = root / source.relative_to(_EXAMPLE)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            target.write_text(source.read_text())
    return root


@needs_kernel
def test_a_clean_catalog_leaves_no_verdict_on_any_asset_it_governs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Recording is evidence-driven, so nothing is written against an asset nobody reported.

    The run still states what it concluded, because a rule that passed is a conclusion, but the
    only subject it can state that against is the repository's own fact table.
    """
    check(clean(tmp_path), select="data_assets", report_only=True, writeback=True)

    output = capsys.readouterr().out
    assert _GOVERNED["urn"] not in output
    assert "published 4 fact datasets" in output


@needs_kernel
def test_a_check_records_nothing_unless_it_is_asked_to(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A check reads evidence and returns none, which is the invariant this path keeps."""
    root = example(tmp_path / "example")

    check(root, select="data_assets", report_only=True)

    output = capsys.readouterr().out
    assert "verdicts recorded" not in output and "nothing was recorded" not in output


@needs_kernel
def test_a_project_can_ask_for_every_run_without_naming_the_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A scheduled job sets `publish_runs`, so the run is recorded with no command-line change."""
    root = example(tmp_path / "example")
    configuration = (root / "pyproject.toml").read_text()
    (root / "pyproject.toml").write_text(configuration + "publish_runs = true\n")

    check(root, select="data_assets", report_only=True)

    assert "verdicts recorded for 5 subjects" in capsys.readouterr().out


def test_a_run_with_no_report_to_point_at_leaves_no_link_behind(tmp_path: Path) -> None:
    """A link nobody can follow is worse than no link, so a placeholder writes none at all.

    The same run also closes the one file its rule used to report and no longer does, which is
    the only thing that ever writes that verdict a second time.
    """
    asked: list[str] = []
    stale: JsonValue = {
        "urn": "urn:li:assertion:stale",
        "info": {"description": "ALL-DATA0002 states something", "externalUrl": ""},
        "runEvents": {
            "total": 1,
            "failed": 1,
            "succeeded": 0,
            "runEvents": [
                {
                    "timestampMillis": 1786096800000,
                    "status": "COMPLETE",
                    "result": {
                        "type": "FAILURE",
                        "nativeResults": [
                            {"key": "rule", "value": "ALL-DATA0002"},
                            {"key": "path", "value": "repaired.py"},
                        ],
                    },
                }
            ],
        },
    }

    async def respond(request: httpx.Request) -> httpx.Response:
        operation = json.loads(request.content)["operationName"]
        asked.append(operation)
        if operation == "MCMRAssertionHistory":
            held = {"dataset": {"assertions": {"total": 1, "assertions": [stale]}}}
            return httpx.Response(200, json={"data": held})
        return httpx.Response(200, json={"data": {"upsertCustomAssertion": {"urn": "urn:li:x"}}})

    context = PublicationContext(
        repository=tmp_path,
        settings={"server": "https://catalog.example", "report_url": "https://example.invalid/x"},
        records=[
            RunRecord(
                rule="ALL-DATA0002",
                subject="urn:li:dataset:(snowflake,orders,PROD)",
                state=RunState.FAILURE,
            )
        ],
    )

    receipts = anyio.run(DataHubProvider(httpx.MockTransport(respond)).publish, context)

    assert "MCMRWriteback" not in asked and "MCMRWritebackLinks" not in asked
    assert receipts[0] == "closed 1 file verdicts"
    assert receipts[1] == (
        "urn:li:dataset:(snowflake,orders,PROD) 1 verdicts recorded "
        "(0 passing, 1 failing), with no report to link"
    )


@needs_kernel
def test_the_recorded_run_records_one_verdict_per_rule_and_asset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every asset a run judged carries its verdicts and still points at the analysis."""
    root = example(tmp_path / "example")

    check(root, select="data_assets", report_only=True, writeback=True)

    output = capsys.readouterr().out.replace("\n", " ")
    assert output.count("verdicts recorded (") == 5
    assert "linked https://github.com/phvv-me/mcmr" in output


def test_a_recorded_verdict_keeps_the_assertion_identity_its_rule_and_asset_share() -> None:
    """A later run lands on the same assertion, which is what makes a timeline one timeline."""
    first = RunRecord(rule="ALL-DATA0002", subject="urn:li:dataset:(snowflake,orders,PROD)")
    again = first.model_copy(update={"state": RunState.FAILURE, "repair": RepairState.APPLIED})
    other = first.model_copy(update={"subject": "urn:li:dataset:(snowflake,invoices,PROD)"})

    assert assertion_urn(first) == assertion_urn(again)
    assert assertion_urn(first) != assertion_urn(other)


@needs_kernel
def test_the_history_of_a_repository_reads_back_what_previous_runs_concluded(
    tmp_path: Path,
) -> None:
    """The read an agent performs before acting states which rule closed and which did not."""
    root = example(tmp_path / "example")
    settings = {
        "recorded": "recordings",
        "report_url": "https://github.com/phvv-me/mcmr",
        "server": "http://recorded.invalid",
    }
    subject = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.analytics.orders,PROD)"

    timelines = anyio.run(
        DataHubProvider().history,
        HistoryContext(repository=root, settings=settings, subjects=[subject]),
    )

    closed = next(item for item in timelines if item.rule == "ALL-DATA0002")
    still = next(item for item in timelines if item.rule == "ALL-DATA0012")
    assert (closed.state, closed.repairs, bool(closed.last_failure)) == (RunState.SUCCESS, 1, True)
    assert (still.state, still.repairs) == (RunState.FAILURE, 0)
    assert closed.since is not None and still.since is not None and closed.since > still.since


def gateway(respond: Responder) -> DataHubGraphQL:
    """Return one opened gateway that answers through the given mock responder."""
    return DataHubGraphQL(
        DataHubSettings(server="https://catalog.example"),
        transport=httpx.MockTransport(respond),
    )


def test_a_result_reported_before_its_new_assertion_settles_is_reported_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DataHub resolves an assertion through an index its own upsert reaches a moment later.

    A live DataHub Core rejects the first result against a brand new custom assertion for about a
    second, which is why a run that upserts and reports in one breath must wait that window out
    instead of failing the whole writeback.
    """
    monkeypatch.setattr(recording_module, "sleep", noop)
    attempts: list[str] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        attempts.append(json.loads(request.content)["operationName"])
        if len(attempts) < 3:
            return httpx.Response(200, json={"errors": [{"message": "does not exist"}]})
        return httpx.Response(200, json={"data": {"reportAssertionResult": True}})

    async def report() -> None:
        async with gateway(respond) as client:
            await DataHubRecording(client, "https://example.invalid/run").report_result({})

    anyio.run(report)

    assert attempts == ["MCMRReportAssertionResult"] * 3


def test_a_result_that_is_wrong_rather_than_early_fails_with_the_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiting cannot fix a malformed request, so the last attempt raises what the server said."""
    monkeypatch.setattr(recording_module, "sleep", noop)

    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "unknown variable type"}]})

    async def report() -> None:
        async with gateway(respond) as client:
            await DataHubRecording(client, "https://example.invalid/run").report_result({})

    with pytest.raises(DataHubRequestError, match="unknown variable type"):
        anyio.run(report)


def test_the_link_an_asset_already_holds_is_not_written_a_second_time() -> None:
    """`addLink` refuses a duplicate, so a run reads first and writes only the missing link."""
    report_url = "https://example.invalid/run"
    subject = "urn:li:dataset:(snowflake,orders,PROD)"
    held = [{"url": report_url, "label": "MCMR policy run"}]
    asked: list[str] = []

    def responder(elements: list[dict[str, str]]) -> Responder:
        async def respond(request: httpx.Request) -> httpx.Response:
            operation = json.loads(request.content)["operationName"]
            asked.append(operation)
            if operation == "MCMRWritebackLinks":
                return httpx.Response(
                    200,
                    json={"data": {"dataset": {"institutionalMemory": {"elements": elements}}}},
                )
            return httpx.Response(200, json={"data": {"addLink": True}})

        return respond

    async def remember(elements: list[dict[str, str]]) -> None:
        async with gateway(responder(elements)) as client:
            await DataHubRecording(client, report_url).remember(subject, label="MCMR policy run")

    anyio.run(partial(remember, []))
    anyio.run(partial(remember, held))

    assert asked == [
        "MCMRWritebackLinks",
        "MCMRWriteback",
        "MCMRWritebackLinks",
    ]


def test_an_applied_repair_is_recorded_on_the_verdict_its_rerun_passed() -> None:
    """A repaired rule passes on the rerun, so its passing verdict is where the edit is stated."""
    subject = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ecommerce.analytics.orders,PROD)"
    span = SourceSpan(path="pipeline.py")
    report = CheckReport(
        root=".",
        failures=[
            RuleFailure(
                rule="ALL-DATA0012",
                summary="Report a tagged field with no glossary term.",
                where="datahub",
                span=span,
                value=1,
                allowed="<= 0",
                findings=[Finding(message=f"field `{subject}.customer_email`", span=span)],
            )
        ],
        passes=[RulePass(rule="ALL-DATA0002", summary="Report an absent field.")],
    )

    records = RunPublication(
        report=report,
        applied=["ALL-DATA0002"],
        repair=RepairMode.APPLY,
    ).records

    repaired = next(record for record in records if record.rule == "ALL-DATA0002")
    assert (repaired.state, repaired.repair, repaired.properties["repair"]) == (
        RunState.SUCCESS,
        RepairState.APPLIED,
        "applied",
    )


def test_every_verdict_of_one_invocation_is_stamped_with_that_invocation() -> None:
    """A reader who opened one rule's timeline can pivot to the run that wrote it, by identity."""
    reported: list[JsonValue] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["operationName"] == "MCMRReportAssertionResult":
            reported.extend(payload["variables"]["properties"])
        return httpx.Response(200, json={"data": {"upsertCustomAssertion": {"urn": "urn:li:x"}}})

    async def record() -> None:
        async with gateway(respond) as client:
            await DataHubRecording(client, "", run="mcmr-orders-1786179600000").record(
                [RunRecord(rule="ALL-DATA0002", subject="urn:li:dataset:(snowflake,orders,PROD)")]
            )

    anyio.run(record)

    assert {"key": "runId", "value": "mcmr-orders-1786179600000"} in reported


def test_a_run_identity_names_the_repository_and_the_moment_it_ran(tmp_path: Path) -> None:
    """Two runs over one repository are two runs, which is what the moment keeps apart."""
    moment = datetime(2026, 8, 8, 9, 0, tzinfo=UTC)

    named = identity(tmp_path, "orders", moment)
    unnamed = identity(tmp_path / "fallback", "", moment)

    assert named == "mcmr-orders-1786179600000"
    assert unnamed == "mcmr-fallback-1786179600000"
    assert identity(tmp_path, "orders") != named


@needs_kernel
def test_a_recorded_run_is_published_beside_the_verdicts_that_name_it(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The whole invocation is recorded once, under the identity every verdict already carries."""
    root = example(tmp_path / "example")

    check(root, select="data_assets", report_only=True, writeback=True)

    output = capsys.readouterr().out.replace("\n", " ")
    assert "recorded run mcmr-example-" in output
    assert "rules and" in output and "failures in" in output


@needs_kernel
def test_a_run_with_nothing_to_conclude_records_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A repository with no source observes nothing, so no rule reached a verdict to store."""
    root = clean(tmp_path)
    (root / "rollup.py").unlink()

    check(root, select="ALL-DUPL0005", report_only=True, writeback=True)

    assert "nothing was recorded" in capsys.readouterr().out
