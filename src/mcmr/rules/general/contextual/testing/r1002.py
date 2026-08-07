from enum import StrEnum, auto

from ..... import Category, rule
from .....execution import ClassificationBackend
from .....execution.queries import ModelQuery
from .....facts import TestStrategyFact
from .....table import Table


class TestIsolation(StrEnum):
    ISOLATED = auto()
    SHARED = auto()
    INTEGRATED = auto()
    OVERMOCKED = auto()
    UNCERTAIN = auto()


@rule(
    "ALL-TEST1002",
    policy=Category.outcomes(good={"integrated", "isolated"}, neutral={"shared", "uncertain"}),
)
def test_isolation(
    subject: Table[TestStrategyFact],
    backend: ClassificationBackend,
) -> ModelQuery[TestIsolation]:
    """Judge whether tests control state without losing meaningful behavior.

    Definition
    ----------
    Compare fixtures, shared state, order dependence, external services, clocks, randomness,
    cleanup, parallel execution, and mock boundaries.

    Evidence
    --------
    Findings cite tests, fixtures, state transitions, order trials, and environment dependencies.

    Exceptions
    ----------
    Integration suites may share expensive infrastructure when isolation is restored between cases.

    Examples
    --------
    A test depending on another test to create a record is `shared`. A database fixture that resets
    state while exercising real queries is `integrated` and isolated.

    References
    ----------
    Cites "xUnit Test Patterns", Independent Test
    Cites "Software Engineering at Google", Test Doubles
    Cites "Test-Driven Development with Python", test isolation
    """
    return backend.classification(
        subject,
        category=TestIsolation,
        instructions=test_isolation.instructions,
    )
