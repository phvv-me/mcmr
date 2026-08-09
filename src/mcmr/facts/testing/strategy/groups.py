from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .failure import FailureScenario


class TestStrategyFields(Fact):
    """Retain requirements, risks, boundaries, scenarios, types, controls, and services."""

    requirements: list[str] = Field(
        default=[], description="behavior requirements the test suite is expected to cover"
    )
    risks: list[str] = Field(
        default=[], description="risk areas the test suite is expected to guard against"
    )
    boundaries: list[str] = Field(
        default=[], description="boundary conditions the test suite is expected to exercise"
    )
    failure_scenarios: list[FailureScenario] = Field(
        default=[], description="failure concerns evaluated for concrete test coverage"
    )
    test_types: list[str] = Field(
        default=[], description="test types present in the suite, such as unit or integration"
    )
    state_controls: list[str] = Field(
        default=[], description="controls the suite uses to isolate and reset shared state"
    )
    external_services: list[str] = Field(
        default=[], description="external services the test suite depends on or mocks"
    )
