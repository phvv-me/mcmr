from typing import TYPE_CHECKING

from pydantic import Field, model_validator

from .groups import OverrideFields

if TYPE_CHECKING:
    from typing import Self

    from ..declarations.member import MemberDeclaration


class OverrideFact(OverrideFields):
    """Describe one inheritance link and how the subclass handles inherited members."""

    ancestor_names: list[str] = Field(
        default=[], description="names of every base above the derived class, resolved or not"
    )
    declared: list[MemberDeclaration] = Field(
        default=[], description="members the derived class writes down itself"
    )
    inherited: list[MemberDeclaration] = Field(
        default=[],
        description="members the derived class inherits from this base, nearest declaration wins",
    )
    initializer_calls: list[str] = Field(
        default=[], description="receivers the derived class's own initializer calls __init__ on"
    )

    @model_validator(mode="after")
    def names_each_member_once(self) -> Self:
        """Require each inheritance side to expose one effective binding per name."""
        for side, declarations in (("declared", self.declared), ("inherited", self.inherited)):
            names = [item.name for item in declarations]
            if len(names) != len(set(names)):
                raise ValueError(f"override link repeats a {side} member name")
        return self
