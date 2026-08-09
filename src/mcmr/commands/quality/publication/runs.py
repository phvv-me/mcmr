from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ....execution.providers import (
    ExternalEvidence,
    HistoryContext,
    ProviderExecutionError,
    PublicationContext,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from pydantic import JsonValue

    from ....domain.contracts import RuleTimeline
    from .records import RunPublication

# The provider-namespaced key a project sets to record every run without naming the flag, which is
# what a scheduled job wants and what an interactive check must never assume.
_ALWAYS = "publish_runs"

# What every identity a run is recorded under begins with, so a catalog holding somebody else's
# runs still says which of them this tool wrote.
_STAMP = "mcmr"


def should_record(settings: Mapping[str, Mapping[str, JsonValue]]) -> bool:
    """Whether any installed provider was configured to record every run it evidences."""
    return any(provider.get(_ALWAYS) is True for provider in settings.values())


def identity(root: Path, repository: str, at: datetime | None = None) -> str:
    """Return the one identity every receiving system records this invocation under.

    A verdict says what one rule concluded, and the identity is what says the verdict came from
    this run rather than the one before it, so a reader who opened a rule timeline can ask what
    else the same invocation did. The moment is what keeps two runs over one repository apart.
    """
    moment = at or datetime.now(UTC)
    named = repository or root.resolve().name
    return f"{_STAMP}-{named}-{int(moment.timestamp() * 1000)}"


async def publish(
    root: Path,
    settings: Mapping[str, Mapping[str, JsonValue]],
    publication: RunPublication,
    label: str,
) -> list[str]:
    """Hand the verdicts of one completed run to every provider that can record them.

    The graph travels with them because a verdict about ordinary source has nowhere to live until
    the tables it was derived from exist, so the same gate that records a run publishes them. The
    run identity is minted once here rather than per provider, because two systems recording the
    same invocation under two names could never be read as one run again.
    """
    evidence = ExternalEvidence.for_repository(root, settings)
    graph = publication.graph
    run = identity(root, graph.repository)
    receipts: list[str] = []
    for name, publisher in evidence.publishers.items():
        receipts.extend(
            await publisher.publish(
                PublicationContext(
                    repository=root,
                    settings=settings.get(name, {}),
                    records=publication.records,
                    label=label,
                    graph=graph,
                    run=run,
                    summary=publication.summary,
                )
            )
        )
    return receipts


async def read(
    root: Path,
    settings: Mapping[str, Mapping[str, JsonValue]],
    subjects: Sequence[str],
) -> list[RuleTimeline]:
    """Read back what every installed provider already recorded about these subjects."""
    evidence = ExternalEvidence.for_repository(root, settings)
    timelines: list[RuleTimeline] = []
    for name, historian in evidence.historians.items():
        context = HistoryContext(
            repository=root,
            settings=settings.get(name, {}),
            subjects=list(subjects),
        )
        try:
            timelines.extend(await historian.history(context))
        except ValueError as error:
            raise ProviderExecutionError(name, error) from None
    return timelines
