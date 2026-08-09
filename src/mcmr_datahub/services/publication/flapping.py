from typing import TYPE_CHECKING

from mcmr.plugins import RunState

from .history import SubjectHistory
from .reported import ReportedFiles

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from mcmr.plugins import RuleTimeline

# How a verdict reads inside the sentence an incident is written in.
_WORDS = {RunState.SUCCESS: "passing", RunState.FAILURE: "failing", RunState.ERROR: "unanswered"}

# The moment format a description states a recorded verdict at, which stays readable in prose.
_MOMENT = "%Y-%m-%d %H%M"


class FlapDetector:
    """Read the recorded timelines of one run and name the subjects that keep changing answer.

    A subject alternates when its verdicts, once the repeats are collapsed, go from failing to
    passing and back to failing. That is two changes, which is the smallest pattern no single
    verdict can explain, and it is read from the history the catalog already holds rather than
    from anything this run had to remember. Whether the subject is failing right now comes from
    what this run itself concluded instead, because the verdict that just closed a file is not yet
    in the index a read would go through. Only a subject on a fact table this same writeback
    published is considered, because raising an incident anywhere else materializes a stub asset.
    """

    def __init__(
        self,
        timelines: Sequence[RuleTimeline],
        published: Iterable[str],
        reported: ReportedFiles | None = None,
    ) -> None:
        self.timelines = timelines
        self.published = set(published)
        self.reported = reported or ReportedFiles()

    def histories(self) -> list[SubjectHistory]:
        """Return what every file-scoped subject on a published fact table recently did."""
        found = [
            self._history(timeline)
            for timeline in self.timelines
            if timeline.subject in self.published and timeline.where
        ]
        return sorted(found, key=lambda item: (item.rule, item.path))

    def scores(self) -> dict[str, int]:
        """Return how much the noisiest subject inside each published fact table moves."""
        found = dict.fromkeys(self.published, 0)
        for timeline in self.timelines:
            if timeline.subject in found:
                found[timeline.subject] = max(found[timeline.subject], self._changes(timeline))
        return found

    @staticmethod
    def _changes(timeline: RuleTimeline) -> int:
        """Return how many times the recorded verdict actually changed, repeats collapsed."""
        return max(len(FlapDetector._states(timeline)) - 1, 0)

    @staticmethod
    def _states(timeline: RuleTimeline) -> list[RunState]:
        """Return the verdicts this timeline passed through, with every repeat collapsed."""
        passed: list[RunState] = []
        for event in timeline.events:
            if not passed or passed[-1] is not event.state:
                passed.append(event.state)
        return passed

    @classmethod
    def _alternates(cls, timeline: RuleTimeline) -> bool:
        """Whether this timeline went failing, then passing, then failing again."""
        states = cls._states(timeline)
        return any(
            (first, second, third) == (RunState.FAILURE, RunState.SUCCESS, RunState.FAILURE)
            for first, second, third in zip(states, states[1:], states[2:], strict=False)
        )

    def _history(self, timeline: RuleTimeline) -> SubjectHistory:
        """Project one recorded timeline into what an incident would have to say about it."""
        observed = [
            f"{_WORDS[event.state]} on {event.at.strftime(_MOMENT)}" for event in timeline.events
        ]
        settled = self.reported.settled(rule=timeline.rule, path=timeline.where)
        return SubjectHistory(
            rule=timeline.rule,
            path=timeline.where,
            subject=timeline.subject,
            changes=self._changes(timeline),
            failing=timeline.state is RunState.FAILURE and not settled,
            alternates=self._alternates(timeline),
            timeline=observed,
        )
