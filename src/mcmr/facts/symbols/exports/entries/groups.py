from patos import FrozenModel
from pydantic import Field, PositiveInt

from .....domain.primitives import NonEmptyStr
from ....foundation import NodeRef


class ExportBypassFields(FrozenModel):
    """Retain bypass identity, replacement, and binding evidence."""

    public_module: NonEmptyStr = Field(
        description="shorter public module the bypassing import could have used instead"
    )
    name: NonEmptyStr = Field(
        description="public name the bypassing import could have reached through that module"
    )
    target: NonEmptyStr = Field(
        description="dotted name the bypassing import actually resolves to"
    )
    expression: NonEmptyStr = Field(
        description="import expression as written at the bypassing site"
    )
    module_node: NodeRef | None = Field(
        default=None, description="syntax node of the module clause in the bypassing import"
    )
    replacement_module: str | None = Field(
        default=None,
        description="shorter public module the bypass could be rewritten to use, when safe",
    )
    binding_count: PositiveInt = Field(
        default=1, description="how many names the bypassing import statement binds"
    )
