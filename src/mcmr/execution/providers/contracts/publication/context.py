from collections.abc import Mapping
from pathlib import Path

from patos import FrozenModel
from pydantic import JsonValue

from .....domain.contracts import RunGraph, RunRecord


class PublicationContext(FrozenModel):
    """Carry one completed run's verdicts to the system that supplied its evidence.

    The records are the run itself rather than a rendering of it, so a receiving system can store
    each verdict against the subject it judged and a later run can be compared with this one. The
    graph beside them states the fact tables the run consumed and the rules that read them, which
    is what gives a verdict about ordinary source somewhere to be stored.
    """

    repository: Path
    settings: Mapping[str, JsonValue] = {}
    records: list[RunRecord] = []
    label: str = "MCMR policy run"
    graph: RunGraph = RunGraph()
