from patos import FrozenModel
from pydantic import Field

from ...foundation import ReceiverKind, Visibility


class AttributeAccessFields(FrozenModel):
    """Retain attribute identity, receiver, and visibility evidence."""

    name: str = Field(description="name of the attribute being accessed")
    receiver_kind: ReceiverKind = Field(
        description="relation of the receiver to the enclosing scope, e.g. self or owner"
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC, description="declared visibility level of the attribute"
    )
    is_inside_owning_class: bool = Field(
        default=False,
        description="whether the access occurs inside its owning class through a self, owner, "
        "or super receiver",
    )
    is_protocol_name: bool = Field(
        default=False,
        description="whether the attribute name is a double-underscore protocol name",
    )
    receiver_text: str = Field(
        default="", description="verbatim source text of the receiver expression"
    )
    receiver_type: str = Field(
        default="", description="name of the local enum type the receiver resolves to, when known"
    )
