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

    from ....domain.contracts import RuleTimeline, RunGraph, RunRecord

# The provider-namespaced key a project sets to record every run without naming the flag, which is
# what a scheduled job wants and what an interactive check must never assume.
_ALWAYS = "publish_runs"


def should_record(settings: Mapping[str, Mapping[str, JsonValue]]) -> bool:
    """Whether any installed provider was configured to record every run it evidences."""
    return any(provider.get(_ALWAYS) is True for provider in settings.values())


async def publish(
    root: Path,
    settings: Mapping[str, Mapping[str, JsonValue]],
    records: Sequence[RunRecord],
    label: str,
    graph: RunGraph,
) -> list[str]:
    """Hand the verdicts of one completed run to every provider that can record them.

    The graph travels with them because a verdict about ordinary source has nowhere to live until
    the tables it was derived from exist, so the same gate that records a run publishes them.
    """
    evidence = ExternalEvidence.for_repository(root, settings)
    receipts: list[str] = []
    for name, publisher in evidence.publishers.items():
        receipts.extend(
            await publisher.publish(
                PublicationContext(
                    repository=root,
                    settings=settings.get(name, {}),
                    records=list(records),
                    label=label,
                    graph=graph,
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
