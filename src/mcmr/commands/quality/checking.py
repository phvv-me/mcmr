from pathlib import Path
from typing import TYPE_CHECKING, Never

import anyio

from ...checking.session import allowed
from ...domain.contracts import FixSafety
from ...execution.providers import ProviderExecutionError
from ...presentation import (
    CheckReport,
    FixResult,
    FixSession,
    PythonFixRenderer,
    RichCheck,
)
from ...presentation.reports import CheckFormat
from ...project import ExecutionOverride
from ..interface import (
    FixPresentation,
    RepairMode,
    RuleCoverage,
    app,
    console,
)
from .analysis import Judgment, judgment
from .publication import RunPublication, publish, read, render, should_record

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import JsonValue

    from ...domain.policy import RulePolicies
    from ...rulebook.catalog import RuleDefinition

# What a present, absent, or negated command flag says about the setting a project already holds.
_STATED = {
    None: ExecutionOverride.UNCHANGED,
    True: ExecutionOverride.ENABLED,
    False: ExecutionOverride.DISABLED,
}


@app.command
def check(
    root: Path = Path(),
    *,
    select: str = "",
    suffixes: str = "",
    kernel: Path | None = None,
    format: CheckFormat = CheckFormat.RICH,
    limit: int = 20,
    repair: RepairMode = RepairMode.NONE,
    maximum_fixes: int = 100,
    output: Path | None = None,
    report_only: bool = False,
    deterministic: bool | None = None,
    contextual: bool | None = None,
    external: bool | None = None,
    rule_coverage: RuleCoverage = RuleCoverage.AVAILABLE,
    writeback: bool | None = None,
    label: str = "MCMR policy run",
) -> None:
    """Run the catalog over a repository and judge it against each rule's effective policy.

    root: repository to analyze.
    select: substring that narrows the selected rules by callable.
    suffixes: comma-separated source suffixes, for a repository in another language.
    kernel: explicit kernel binary, otherwise the one built from this checkout.
    format: `rich` for structured detail, `full` for plain diagnostics, `concise` for one line,
        or `json` for the complete machine-readable report.
    limit: how many detailed diagnostics the report shows.
    repair: `preview` available patches, `apply` safe plans, or `apply-review` review plans
        through verified fixpoints.
    maximum_fixes: bound the number of verified edits in one run.
    output: optional path that receives the complete JSON report.
    report_only: report failures without returning a failing process status.
    deterministic: enable or disable rules computed from repository facts.
    contextual: enable or disable rules estimated by the configured contextual backend.
    external: permit enabled rules to collect current network evidence in memory.
    rule_coverage: use `all` to fail when any selected rule could not execute.
    writeback: record this run's verdicts back to the systems that supplied its evidence,
        or suppress recording a project already asked for.
    label: the label each recorded verdict and institutional memory link carries.
    """
    analysis = judgment(
        root,
        select=select,
        suffixes=suffixes,
        kernel=kernel,
        failure_limit=None,
        deterministic=_STATED[deterministic],
        contextual=_STATED[contextual],
        external=_STATED[external],
    )
    with console.status("Analyzing the repository", spinner="dots"):
        try:
            result = analysis.run()
        except ProviderExecutionError as error:
            _fail_provider(error)
        report = CheckReport.of(root, result)
    fixed = _apply_repairs(root, analysis, report, repair, maximum_fixes)
    report = fixed.report
    if output is not None:
        output.write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    if format is CheckFormat.RICH:
        console.print(RichCheck(limit=limit).render(report))
    else:
        console.print(
            format.check(limit).render(report),
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
    _present_repairs(root, fixed, repair, maximum_fixes)
    _record_run(
        root,
        RunPublication(
            report=fixed.report,
            graph=result.graph,
            applied=[fix.rule for fix in fixed.applied],
            refused=[refusal.rule for refusal in fixed.refused],
            repair=repair,
        ),
        analysis.configuration.providers,
        stated=_STATED[writeback],
        label=label,
    )
    incomplete = rule_coverage is RuleCoverage.ALL and report.skipped_rule_count
    if (report.failure_count or incomplete) and not report_only:
        raise SystemExit(1)


@app.command
def history(
    root: Path = Path(),
    *,
    select: str = "",
    assets: tuple[str, ...] = (),
    kernel: Path | None = None,
) -> None:
    """Read what previous runs already concluded about the governed assets this repository names.

    Nothing here judges the repository. An agent about to change a pipeline reads this first, so
    it learns which rule has been failing since when, which repairs already landed, and why the
    last failure fired, instead of discovering all of it again. Learning which subjects a
    repository names never needs a model's opinion or a network read the project did not already
    ask for, so this read runs neither lane beyond what the configuration already enabled.

    root: repository whose governed assets are looked up.
    select: substring that narrows the analyzed rules by callable when assets are not named.
    assets: an asset identity to read directly, repeatable, skipping the analysis entirely.
    kernel: explicit kernel binary, otherwise the one built from this checkout.
    """
    analysis = judgment(
        root,
        select=select,
        suffixes="",
        kernel=kernel,
        contextual=ExecutionOverride.DISABLED,
    )
    try:
        timelines = anyio.run(
            read,
            root,
            analysis.configuration.providers,
            list(assets) or _named(root, analysis),
        )
    except ProviderExecutionError as error:
        _fail_provider(error)
    if not timelines:
        console.print("No previous run was recorded for the assets this repository names.")
        return
    render(timelines)


def _named(root: Path, analysis: Judgment) -> list[str]:
    """Return the subjects this repository records against, which is what keys a timeline."""
    with console.status("Reading the subjects this repository names", spinner="dots"):
        judged = analysis.run()
        report = CheckReport.of(root, judged)
    return RunPublication(report=report, graph=judged.graph).subjects


def _record_run(
    root: Path,
    publication: RunPublication,
    settings: Mapping[str, Mapping[str, JsonValue]],
    *,
    stated: ExecutionOverride,
    label: str,
) -> None:
    """Record this run's verdicts only when the caller or the project asked for it.

    A check reads evidence and returns none of its own unless somebody says so, which is why the
    default path never reaches a provider. The verdicts come from the report this run already
    produced, so nothing is analyzed twice.
    """
    asked = (
        should_record(settings)
        if stated is ExecutionOverride.UNCHANGED
        else stated is ExecutionOverride.ENABLED
    )
    if not asked:
        return
    records = publication.records
    if not records:
        console.print("No subject was named by this run, so nothing was recorded.")
        return
    with console.status("Recording this run", spinner="dots"):
        receipts = anyio.run(publish, root, settings, records, label, publication.graph)
    for receipt in receipts:
        console.print(receipt)
    subjects = len({record.subject for record in records})
    console.print(f"{len(records)} verdicts recorded for {subjects} subjects.")


def _fail_provider(error: ProviderExecutionError) -> Never:
    """Present one external provider boundary failure and leave without a traceback."""
    console.print(str(error), style="red")
    raise SystemExit(2) from None


def _apply_repairs(
    root: Path,
    analysis: Judgment,
    report: CheckReport,
    repair: RepairMode,
    maximum_fixes: int,
) -> FixResult:
    """Apply the explicitly selected safety class through a verified fixpoint."""
    if repair not in {RepairMode.APPLY, RepairMode.APPLY_REVIEW}:
        return FixResult(report=report)
    safety = FixSafety.REVIEW if repair is RepairMode.APPLY_REVIEW else FixSafety.SAFE
    with console.status(f"Applying and verifying {safety} fixes", spinner="dots"):
        return FixSession(
            root,
            analysis,
            safety=safety,
            maximum_fixes=maximum_fixes,
        ).run(report)


def _present_repairs(
    root: Path,
    fixed: FixResult,
    repair: RepairMode,
    maximum_fixes: int,
) -> None:
    """Show applied plans beside every remaining review or rendering refusal."""
    if repair is RepairMode.NONE:
        return
    preview_safety = None if repair is RepairMode.PREVIEW else FixSafety.REVIEW
    previewed, preview_refusals = PythonFixRenderer(root).available(
        fixed.report,
        preview_safety,
        maximum=maximum_fixes,
    )
    refused = list(fixed.refused)
    refused.extend(item for item in preview_refusals if item not in refused)
    FixPresentation(console).show(
        applied=fixed.applied,
        previewed=previewed,
        refused=refused,
    )


def allowance(policies: RulePolicies, definition: RuleDefinition) -> str:
    """Render what the effective policy allows for one rule."""
    return allowed(
        policies.policy(
            rule_id=definition.id,
            candidate=definition.policy,
        )
    )
