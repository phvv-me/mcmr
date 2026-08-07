from pathlib import Path
from shutil import copytree
from tempfile import mkdtemp
from time import perf_counter
from typing import TYPE_CHECKING

from ...presentation.reports import CheckFormat
from ..interface import RepairMode, app, console
from .checking import check, history

if TYPE_CHECKING:
    from collections.abc import Callable

# The rule the recorded catalog proves a repair for, which is the one the clean rerun answers.
_REPAIRED = "missing_data_field_reference"

# The whole DataHub rule family, selected by the package every one of those rules lives in.
_FAMILY = "data_assets"

# What the copied workspace is called, so the fact tables the run publishes are named after the
# pipeline rather than after whichever temporary directory the copy landed in.
_REPOSITORY = "ecommerce-pipeline"


@app.command
def demo(example: Path = Path("examples/datahub")) -> None:
    """Run the complete DataHub workflow over a recorded catalog with no running service.

    The story is one converging pipeline. A run states what the catalog says, repairs the one
    change the catalog proves, records every verdict as a DataHub assertion, and the last step
    reads that history back the way the next agent would before touching the same file.

    example: the recorded DataHub example, copied into a fresh workspace before anything is edited.
    """
    workspace = Path(mkdtemp(prefix="mcmr-demo-")) / _REPOSITORY
    copytree(example, workspace, dirs_exist_ok=True)
    console.print(f"Workspace {workspace}", style="dim")
    elapsed = {
        "review": _timed(
            "1. What the catalog says about this change",
            _checked(workspace, _FAMILY),
        ),
        "preview": _timed(
            "2. The repair the catalog proves",
            _checked(workspace, _REPAIRED, repair=RepairMode.PREVIEW),
        ),
        "apply": _timed(
            "3. The repair applied and verified by a rerun",
            _checked(workspace, _REPAIRED, repair=RepairMode.APPLY),
        ),
        "record": _timed(
            "4. Every verdict recorded as a DataHub assertion",
            _checked(workspace, _FAMILY, writeback=True),
        ),
        "history": _timed(
            "5. What the next agent reads before touching this pipeline",
            lambda: history(workspace, select=_FAMILY),
        ),
    }
    total = sum(elapsed.values())
    timings = "  ".join(f"{name} {seconds:.2f}s" for name, seconds in elapsed.items())
    console.print(f"\n{timings}  total {total:.2f}s")


def _checked(
    workspace: Path,
    select: str,
    *,
    repair: RepairMode = RepairMode.NONE,
    writeback: bool = False,
) -> Callable[[], None]:
    """Return one bound check over the recorded catalog, ready for the step that times it."""

    def run() -> None:
        check(
            workspace,
            select=select,
            format=CheckFormat.CONCISE,
            repair=repair,
            external=True,
            report_only=True,
            writeback=writeback,
        )

    return run


def _timed(title: str, step: Callable[[], None]) -> float:
    """Run one demonstration step under its heading and return its wall time."""
    console.print(f"\n[bold]{title}[/bold]")
    started = perf_counter()
    step()
    return perf_counter() - started
