from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mcmr.plugins import RuleTimeline


class RuleVerdicts:
    """State what each rule's recorded timeline currently says, by rule identity.

    One rule keeps a repository-wide timeline beside one per file it reported, and the
    repository-wide one is the state of the rule itself, so a rule naming files is still
    summarized by the timeline that closes when the whole rule stops failing. A contextual rule
    also states what it has cost here, once for its whole history and once for the run that just
    finished, because a rule failing forever cheaply is a different problem from one failing
    forever expensively.
    """

    def __init__(self, timelines: Sequence[RuleTimeline]) -> None:
        self.stated = self._summarized(timelines)

    def of(self, rule: str) -> dict[str, str]:
        """Return what one rule currently states here, or nothing when nothing was recorded."""
        return self.stated.get(rule, {})

    @staticmethod
    def _summarized(timelines: Sequence[RuleTimeline]) -> dict[str, dict[str, str]]:
        """Return the one timeline that speaks for each rule, file-scoped ones passed over."""
        summarized: dict[str, dict[str, str]] = {}
        for timeline in sorted(timelines, key=lambda item: bool(item.where)):
            recorded = timeline.events[-1] if timeline.events else None
            if timeline.rule in summarized or recorded is None:
                continue
            began = timeline.since or recorded.at
            spent = timeline.tokens
            summarized[timeline.rule] = {
                "lastResult": str(timeline.state).upper(),
                "lastRun": recorded.at.isoformat(timespec="seconds"),
                "since": began.isoformat(timespec="seconds"),
                "findings": recorded.properties.get("findings", "0"),
                "tokens": str(spent) if spent else "",
                "lastRunTokens": str(recorded.tokens) if recorded.tokens else "",
            }
        return summarized
