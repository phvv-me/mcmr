from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .group import TestCaseGroup
    from .loop import LiteralTestLoop


class TestCaseGroupFact(Fact):
    """Describe one related group of test cases."""

    groups: list[TestCaseGroup] = Field(
        default=[],
        description="sibling tests sharing the same syntax once their literals are removed",
    )
    loops: list[LiteralTestLoop] = Field(
        default=[], description="test-owned loops that walk a table of literal cases"
    )
