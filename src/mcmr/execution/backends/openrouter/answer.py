from enum import StrEnum

from patos import FrozenModel

from ...queries.contracts import Assessment, Classification
from .planning import RepositoryRule


class RepositoryAnswer(FrozenModel):
    """Carry one answered rule slice back to its original candidate positions."""

    rule: RepositoryRule
    outcomes: list[Classification[StrEnum] | Assessment]
