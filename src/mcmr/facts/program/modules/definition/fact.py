from typing import TYPE_CHECKING, Literal

from patos import FrozenModel
from pydantic import Field

from .groups import ModuleFields

if TYPE_CHECKING:
    from ....foundation import NodeRef


class ModuleFact(ModuleFields):
    """Describe one source module and its resolved members."""

    class Member(FrozenModel):
        """Describe one member a source module declares."""

        name: str = Field(description="name of the declared member")
        kind: Literal["class", "function", "unknown"] = Field(
            default="unknown", description="kind of declaration the member is"
        )
        source: str = Field(
            default="", description="verbatim source text of the member's declaration"
        )

    is_test: bool = Field(default=False, description="whether the module is a test module")
    declares_all: bool = Field(
        default=False, description="whether the module declares or extends `__all__`"
    )
    all_declarations: list[NodeRef] = Field(
        default=[], description="syntax nodes of every `__all__` declaration statement"
    )
    has_only_imports_and_all: bool = Field(
        default=False,
        description="whether the module's body is only imports and an `__all__` declaration",
    )
    members: list[Member] = Field(
        default=[], description="top-level classes and functions the module declares"
    )
