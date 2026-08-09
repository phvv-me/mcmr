from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from pydantic import NonNegativeInt, PositiveInt

    pass


class OverrideFields(Fact):
    """Retain override endpoints, depth, counts, decorators, and base names."""

    derived: str = Field(
        default="", description="qualified name of the subclass in this inheritance link"
    )
    base: str = Field(
        default="", description="qualified name of the ancestor in this inheritance link"
    )
    depth: PositiveInt = Field(
        default=1, description="inheritance steps separating the derived class from this base"
    )
    overridden_member_count: NonNegativeInt = Field(
        default=0,
        description="declared members that also appear among the base's inherited members",
    )
    derived_decorators: list[str] = Field(
        default=[], description="decorators applied to the derived class itself"
    )
    base_decorators: list[str] = Field(
        default=[], description="decorators applied to the base class itself"
    )
    base_names: list[str] = Field(
        default=[], description="plain names of every base the derived class states directly"
    )
