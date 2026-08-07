from enum import StrEnum, auto

from ..... import Category, rule
from .....execution import ClassificationBackend
from .....execution.queries import ModelQuery
from .....facts import ChangeFact
from .....table import Table


class ChangeReviewability(StrEnum):
    FOCUSED = auto()
    ENTANGLED = auto()
    OVERSIZED = auto()
    MECHANICAL = auto()
    INCOMPLETE = auto()
    UNCERTAIN = auto()


@rule(
    "ALL-REVI1001",
    policy=Category.outcomes(good={"focused", "mechanical"}, neutral={"uncertain"}),
)
def change_reviewability(
    subject: Table[ChangeFact],
    backend: ClassificationBackend,
) -> ModelQuery[ChangeReviewability]:
    """Judge whether one change can be reviewed with reasonable confidence.

    Definition
    ----------
    Compare stated intent, changed concerns, size, generated portions, tests, risk, rollout,
    ownership, and possible decomposition. Line count is evidence rather than the verdict.

    Evidence
    --------
    Findings cite change groups, intent, tests, risk, generated output, and review dependencies.

    Exceptions
    ----------
    Mechanical migrations may be large when generation and semantic verification are reproducible.

    Examples
    --------
    A feature mixed with unrelated renaming and dependency upgrades is `entangled`. A generated API
    refresh with a reproducible schema diff is `mechanical`.

    References
    ----------
    Cites "Google Engineering Practices", small CLs
    Cites "Software Engineering at Google", Code Review
    Cites "Best Kept Secrets of Peer Code Review", code review effectiveness
    """
    return backend.classification(
        subject,
        category=ChangeReviewability,
        instructions=change_reviewability.instructions,
    )
