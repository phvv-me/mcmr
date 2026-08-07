from collections.abc import Mapping
from pathlib import Path

from patos import FrozenModel
from pydantic import JsonValue


class HistoryContext(FrozenModel):
    """Name the governed subjects whose recorded verdicts one command wants to read."""

    repository: Path
    settings: Mapping[str, JsonValue] = {}
    subjects: list[str] = []
