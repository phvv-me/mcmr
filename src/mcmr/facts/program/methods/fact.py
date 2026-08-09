from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .group import MethodCloneGroup


class MethodGroupFact(Fact):
    """Describe one related group of methods."""

    groups: list[MethodCloneGroup] = Field(
        default=[], description="method definitions grouped by identical normalized body"
    )
