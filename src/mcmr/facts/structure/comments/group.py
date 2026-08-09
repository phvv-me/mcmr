from typing import TYPE_CHECKING

from pydantic import Field

from .groups import CommentGroupFields

if TYPE_CHECKING:
    from ...foundation import NodeRef


class CommentGroup(CommentGroupFields):
    """Retain measured sizes for one contiguous comment group."""

    parses_as_source: bool = Field(
        default=False,
        description="whether the comment body parses as valid source rather than prose",
    )
    is_directive: bool = Field(
        default=False, description="whether the comment is a tool directive rather than prose"
    )
    node: NodeRef | None = Field(
        default=None, description="syntax node the comment group occupies, when captured"
    )
