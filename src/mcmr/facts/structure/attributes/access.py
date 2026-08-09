from typing import TYPE_CHECKING

from pydantic import Field

from .groups import AttributeAccessFields

if TYPE_CHECKING:
    from ...foundation import NodeRef


class AttributeAccess(AttributeAccessFields):
    """Retain one member access, its visibility, and owner relationship."""

    receiver_type_bases: list[str] = Field(
        default=[],
        description="base class names of the receiver's resolved enum type, when known",
    )
    node: NodeRef = Field(description="syntax node the attribute access expression occupies")
