from patos import FrozenModel
from pydantic import Field

from ...foundation import Fact, NodeRef
from .expression import Expression


class CallFact(Fact):
    """Describe one resolved callable invocation."""

    class SiteIdentity(FrozenModel):
        """Retain one call's identity, inputs, receiver, and assignment."""

        qualified_name: str = Field(description="dotted name the call resolves to")
        path: str = Field(description="repository relative path where the call site occurs")
        arguments: list[Expression] = Field(
            default=[], description="positional expressions passed to the call"
        )
        keyword_names: list[str] = Field(
            default=[], description="names of keyword arguments passed to the call"
        )
        receiver: Expression | None = Field(
            default=None, description="expression the call is invoked on, when it is a method call"
        )
        assigned_target: str = Field(
            default="", description="name the call result is bound to, empty when unused"
        )

    class SiteResolution(SiteIdentity):
        """Retain the source and resolution state for one call."""

        result_is_discarded: bool = Field(
            default=False,
            description="whether the call is a bare statement whose result is never used",
        )
        node: NodeRef = Field(description="syntax node the call expression occupies")
        callee: NodeRef | None = Field(
            default=None,
            description="syntax node of the callee, when distinct from the call itself",
        )
        target_id: str = Field(
            default="", description="identifier of the resolved callee in the dependency graph"
        )
        is_external: bool = Field(
            default=False, description="whether the resolved callee lives outside the repository"
        )
        is_standard_library: bool = Field(
            default=False,
            description="whether the resolved callee lives in the language standard library",
        )
        is_first_party: bool = Field(
            default=False, description="whether the resolved callee lives inside this repository"
        )

    class SiteBehavior(SiteResolution):
        """Retain construction, alias, decorator, and async call behavior."""

        is_constructor: bool = Field(
            default=False, description="whether the call constructs an instance of a type"
        )
        is_shadowed: bool = Field(
            default=False,
            description="whether the call's apparent name is shadowed by a local rebinding",
        )
        has_ambiguous_alias: bool = Field(
            default=False,
            description="whether the call's name resolves through an ambiguous alias",
        )
        is_decorator_factory: bool = Field(
            default=False, description="whether the call is a decorator that is itself invoked"
        )
        has_starred_arguments: bool = Field(
            default=False, description="whether the call passes starred or spread arguments"
        )
        enclosing_is_async: bool = Field(
            default=False, description="whether the call occurs inside an async function"
        )

    class Site(SiteBehavior):
        """Retain one resolved call and its shared source facts."""

    calls: list[Site] = Field(default=[], description="resolved calls this fact retains")
    module_bindings: list[str] = Field(
        default=[], description="names declared at module level, used to detect shadowing"
    )
    is_test: bool = Field(default=False, description="whether the fact comes from a test module")
