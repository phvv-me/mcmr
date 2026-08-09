import re
from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import NonNegativeFloat

from ....domain.contracts import (
    RepairState,
    RuleCounts,
    RunGraph,
    RunRecord,
    RunState,
    RunSummary,
)
from ....presentation.reports import CheckReport
from ...interface import RepairMode

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ....domain.contracts import Finding
    from ....presentation.reports import RuleFailure

# The canonical governed identity a finding message carries, which is what a verdict is stored
# against whenever a rule reads a catalog the repository does not own.
_SUBJECT = re.compile(r"urn:li:[a-zA-Z]+:\([^)]*\)")

# What a subject already owned by another system starts with, which is the one shape a verdict
# keeps anchoring on instead of moving to a fact table this run published.
_GOVERNED = "urn:li:"

# How many finding messages one verdict carries, so a subject with a long tail stays readable.
_REASONS = 3


class RunPublication(FrozenModel):
    """Project one completed run into the verdicts a receiving system stores against a subject.

    The projection reads the report the run already produced beside the rules whose repair was
    applied or refused. Nothing here judges again, so the verdicts state exactly what the reader
    on screen was shown, including how far each offered repair got.

    A rule that named a governed asset keeps storing its verdict there, because that asset is a
    subject somebody else already owns. Every other rule anchors on the fact dataset the run
    published for its primary table, which is the closest thing a repository has to a subject a
    catalog can hold, and the file a finding named travels with the verdict as its identity.
    """

    report: CheckReport
    graph: RunGraph = RunGraph()
    applied: list[str] = []
    refused: list[str] = []
    repair: RepairMode = RepairMode.NONE
    elapsed_milliseconds: NonNegativeFloat = 0.0

    @property
    def records(self) -> list[RunRecord]:
        """Return one verdict per subject and rule the run judged, failures first.

        A rule whose repair landed passes on the rerun, so its verdict is the one place the
        applied edit can be stated. Dropping the repair there would leave every recorded timeline
        claiming no repair ever succeeded.
        """
        failed = self._failed()
        owned = (subject for _, subject in failed if subject.startswith(_GOVERNED))
        return [*failed.values(), *self._passed(list(dict.fromkeys(owned)))]

    @property
    def repairs(self) -> dict[str, RepairState]:
        """Return how far this run carried the repair each rule offered."""
        offered = {
            RepairMode.NONE: RepairState.OFFERED,
            RepairMode.PREVIEW: RepairState.PREVIEWED,
            RepairMode.APPLY: RepairState.OFFERED,
            RepairMode.APPLY_REVIEW: RepairState.OFFERED,
        }[self.repair]
        states = {
            failure.rule: offered
            for failure in self.report.failures
            if any(finding.repair is not None for finding in failure.findings)
        }
        return (
            states
            | dict.fromkeys(self.refused, RepairState.REFUSED)
            | dict.fromkeys(self.applied, RepairState.APPLIED)
        )

    @property
    def subjects(self) -> list[str]:
        """Return every subject this run recorded a verdict against, in first-reported order."""
        return list(dict.fromkeys(record.subject for record in self.records))

    @property
    def summary(self) -> RunSummary:
        """Return how much this whole invocation reached, beside what its model turns cost."""
        report = self.report
        return RunSummary(
            files=report.file_count,
            facts=report.fact_count,
            failures=report.failure_count,
            findings=report.finding_count,
            rules=RuleCounts(
                executed=report.rule_execution_count,
                failing=len({failure.rule for failure in report.failures}),
                by_lane=self.graph.lane_counts,
            ),
            duration_milliseconds=self.elapsed_milliseconds,
            spend=self.graph.spent,
        )

    @staticmethod
    def _confidence(failure: RuleFailure) -> float | None:
        """Return the model confidence a contextual rule stated, as a unit fraction."""
        estimated: list[float] = [
            measurement.value / 100.0
            for finding in failure.reported
            if finding.provenance is not None
            for measurement in finding.measurements
            if measurement.name.endswith("confidence")
        ]
        return min(estimated) if estimated else None

    @staticmethod
    def _paths(failure: RuleFailure) -> list[str]:
        """Return the source files one failure reported, in first-reported order."""
        return list(dict.fromkeys(finding.span.path for finding in failure.reported))

    @staticmethod
    def _reasoning(failure: RuleFailure) -> str:
        """Return what the model said, which only a contextual rule carries."""
        reasoned: list[Finding] = [
            finding for finding in failure.reported if finding.provenance is not None
        ]
        return reasoned[0].message if reasoned else ""

    @staticmethod
    def _reasons(failure: RuleFailure) -> list[str]:
        """Return every message one failure reported, in first-reported order."""
        return [finding.message for finding in failure.reported]

    @staticmethod
    def _subjects(failure: RuleFailure) -> list[str]:
        """Return the governed identities one failure named, in first-reported order."""
        named = [
            match for finding in failure.reported for match in _SUBJECT.findall(finding.message)
        ]
        return list(dict.fromkeys(named))

    def _failed(self) -> dict[tuple[str, str], RunRecord]:
        """Return one verdict per failed rule and named subject, keyed by that identity."""
        found: dict[tuple[str, str], RunRecord] = {}
        for failure in self.report.failures:
            for record in self._failures(failure):
                found.setdefault((failure.rule, record.anchor), record)
        return found

    def _failure(
        self,
        failure: RuleFailure,
        subject: str,
        *,
        identity: str = "",
        path: str = "",
        reasons: Sequence[str],
    ) -> RunRecord:
        """Return the verdict one failed rule reached about one subject it named."""
        return RunRecord(
            rule=failure.rule,
            subject=subject,
            identity=identity,
            path=path,
            summary=failure.summary,
            state=RunState.FAILURE,
            lane=self.graph.lane(failure.rule),
            measurement=f"{failure.value} (allowed {failure.allowed})",
            finding_count=len(reasons),
            reasons=list(reasons[:_REASONS]),
            repair=self.repairs.get(failure.rule, RepairState.NONE),
            reasoning=self._reasoning(failure),
            confidence=self._confidence(failure),
            spend=self.graph.spend(failure.rule, path=path),
        )

    def _failures(self, failure: RuleFailure) -> list[RunRecord]:
        """Return every verdict one failed rule states, at the subjects it can be stored on.

        A rule that named governed assets states one verdict per asset, since each of those is a
        subject somebody else owns. Every other rule states one verdict about the whole fact
        dataset, which is the timeline that closes when the rule stops failing, and one more per
        file it reported, which is the detail an agent opens next.
        """
        if governed := self._subjects(failure):
            return [
                self._failure(
                    failure,
                    subject,
                    reasons=[item for item in self._reasons(failure) if subject in item],
                )
                for subject in governed
            ]
        anchor = self.graph.anchor(failure.rule)
        if not anchor:
            return []
        located = [
            self._failure(
                failure,
                anchor,
                identity=f"{path} {failure.where}",
                path=path,
                reasons=[
                    finding.message for finding in failure.reported if finding.span.path == path
                ],
            )
            for path in self._paths(failure)
        ]
        return [self._failure(failure, anchor, reasons=self._reasons(failure)), *located]

    def _passed(self, assets: list[str]) -> list[RunRecord]:
        """Return one passing verdict per rule, on every subject that rule can be stored on."""
        repairs = self.repairs
        return [
            RunRecord(
                rule=rule.rule,
                subject=subject,
                summary=rule.summary,
                state=RunState.SUCCESS,
                lane=self.graph.lane(rule.rule),
                repair=repairs.get(rule.rule, RepairState.NONE),
                spend=self.graph.spend(rule.rule),
            )
            for rule in self.report.passes
            for subject in [*assets, *filter(None, [self.graph.anchor(rule.rule)])]
        ]
