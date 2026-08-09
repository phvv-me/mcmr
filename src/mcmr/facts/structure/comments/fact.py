from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .group import CommentGroup


class CommentFact(Fact):
    """Describe one contiguous source comment."""

    groups: list[CommentGroup] = Field(
        default=[], description="contiguous comment groups this file states"
    )
