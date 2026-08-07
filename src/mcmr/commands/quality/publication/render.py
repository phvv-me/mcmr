from typing import TYPE_CHECKING

from rich.table import Table

from ....domain.contracts import RunState
from ...interface import console

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ....domain.contracts import RuleTimeline

# What each recorded state is called in a sentence about an asset somebody is about to change.
_STATE = {
    RunState.SUCCESS: ("passing since", "green"),
    RunState.FAILURE: ("failing since", "red"),
    RunState.ERROR: ("unanswered since", "yellow"),
}


def render(timelines: Sequence[RuleTimeline]) -> None:
    """Show what every recorded run concluded, grouped by the asset each timeline judges."""
    ordered = sorted(timelines, key=lambda item: (item.subject, item.rule, item.where))
    shown = ""
    for timeline in ordered:
        if timeline.subject != shown:
            console.print(f"\n[bold]{_named_asset(timeline.subject)}[/bold]")
            shown = timeline.subject
        console.print(_line(timeline))


def _line(timeline: RuleTimeline) -> Table:
    """Return one rule's recorded trend as a borderless row a reader scans in one pass."""
    phrase, style = _STATE[timeline.state]
    since = timeline.since.strftime("%Y-%m-%d %H:%M") if timeline.since else "an unknown run"
    detail = ", ".join(part for part in (_repairs(timeline.repairs), _reason(timeline)) if part)
    row = Table.grid(padding=(0, 2))
    row.add_column(no_wrap=True)
    row.add_column(no_wrap=True, style=style)
    row.add_column(overflow="fold")
    row.add_row(f"  {timeline.rule} {timeline.where}".rstrip(), f"{phrase} {since}", detail)
    return row


def _named_asset(subject: str) -> str:
    """Return the readable name inside one governed identity, which is what a person searches."""
    inner = subject.partition("(")[2].rstrip(")")
    return inner.split(",")[1] if inner.count(",") >= 2 else subject


def _reason(timeline: RuleTimeline) -> str:
    """Return why this rule last failed, said as history when a later run already closed it."""
    stated = timeline.last_failure.replace(timeline.subject, _named_asset(timeline.subject))
    if not stated or timeline.state is RunState.FAILURE:
        return stated
    return f"previously {stated}"


def _repairs(applied: int) -> str:
    """Return how many recorded runs closed this rule with an edit, when any did."""
    return (
        f"{applied} repair applied"
        if applied == 1
        else f"{applied} repairs applied"
        if applied
        else ""
    )
