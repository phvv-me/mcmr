from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import Field

from ...foundation import Fact, NodeRef

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from ..suite.quarantined import QuarantinedTest
    from .call import TestCallSite
    from .function import TestFunction


class TestFunctionFact(Fact):
    """Describe one test function and its fixtures and assertions."""

    class FunctionIdentity(FrozenModel):
        """Retain test identity, source, collection, async, and fixture evidence."""

        name: str = Field(description="name of the collected test function")
        path: str = Field(description="repository relative path where the test is declared")
        node: NodeRef | None = Field(
            default=None, description="syntax node the test function occupies"
        )
        is_collected: bool = Field(
            default=True,
            description="whether a runner actually collects this test, false when nested",
        )
        is_async: bool = Field(default=False, description="whether the test function is async")
        fixture_names: list[str] = Field(
            default=[],
            description="fixtures this test reaches, including those requested by other fixtures",
        )
        requested_fixture_names: list[str] = Field(
            default=[], description="fixture names this test requests directly as parameters"
        )

    class FunctionBehavior(FunctionIdentity):
        """Retain marks, calls, body shape, literals, assertions, and targets."""

        marks: list[str] = Field(
            default=[], description="decorator names applied to the test, including pytest marks"
        )
        calls: list[TestCallSite] = Field(default=[], description="calls this test's body makes")
        body_shape: str = Field(
            default="", description="test body with every literal replaced by a placeholder"
        )
        literal_values: list[str] = Field(
            default=[], description="literal values the test body states, in source order"
        )
        assertion_shapes: list[str] = Field(
            default=[], description="normalized shape of each assert statement the test body owns"
        )
        direct_targets: list[str] = Field(
            default=[],
            description="qualified names of the production declarations this test calls directly",
        )
        reachable_targets: list[str] = Field(
            default=[],
            description="qualified names of every production declaration this test's calls reach",
        )

    class FunctionExecution(FunctionBehavior):
        """Retain owned structure, mutation, and parameterization metrics."""

        module_state_mutation_count: NonNegativeInt = Field(
            default=0, description="times the test writes to state its module shares across tests"
        )
        owned_conditional_count: NonNegativeInt = Field(
            default=0, description="if statements the test body owns directly"
        )
        owned_statement_count: NonNegativeInt = Field(
            default=0, description="statements the test body owns, excluding its docstring"
        )
        parametrized_range_sizes: list[NonNegativeInt] = Field(
            default=[],
            description="case counts of each static range() parametrization the test declares",
        )
        generated_parametrization_count: NonNegativeInt = Field(
            default=0,
            description="parametrize decorators whose cases come from a generated comprehension",
        )

    tests: list[TestFunction] = Field(
        default=[], description="collected test functions this file declares"
    )
    quarantined_tests: list[QuarantinedTest] = Field(
        default=[], description="explicit flaky-test quarantines this file declares"
    )
