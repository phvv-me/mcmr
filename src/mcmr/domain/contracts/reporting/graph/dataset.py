from patos import FrozenModel
from pydantic import NonNegativeInt

from ....primitives import NonEmptyStr
from .column import FactColumn


class FactDataset(FrozenModel):
    """State one fact family the run materialized as the dataset its verdicts anchor on."""

    family: NonEmptyStr
    name: NonEmptyStr
    description: str = ""
    columns: list[FactColumn] = []
    row_count: NonNegativeInt = 0
