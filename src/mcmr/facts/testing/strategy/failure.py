from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr


class FailureScenario(FrozenModel):
    """Retain one failure concern and the concrete outcomes its tests assert."""

    name: NonEmptyStr = Field(description="name of the failure concern this scenario tests")
    source_paths: list[str] = Field(
        default=[], description="source paths implicated in this failure concern"
    )
    expected_outcomes: list[str] = Field(
        default=[], description="outcomes the failure concern is expected to produce"
    )
    tests: list[str] = Field(
        default=[], description="names of tests that exercise this failure concern"
    )
    asserted_outcomes: list[str] = Field(
        default=[], description="outcomes the exercising tests actually assert"
    )
    alternative_evidence: str = Field(
        default="",
        description="non-test evidence cited in place of a missing test, when any exists",
    )
