from typing import TYPE_CHECKING

from pydantic import Field

from .groups import TypeAnnotationFields

if TYPE_CHECKING:
    from typing import Literal

    from ...foundation import NodeRef


class TypeAnnotation(TypeAnnotationFields):
    """Retain one resolved annotation and reusable constraint recipe."""

    is_field_specific_metadata: bool = Field(
        default=False,
        description="whether the annotation carries per-field metadata like a description",
    )
    role: Literal["alias", "parameter", "return", "variable"] = Field(
        default="variable", description="kind of declaration this annotation is written on"
    )
    is_external_boundary: bool = Field(
        default=False,
        description="whether the annotation sits on a CLI command or callback parameter or return",
    )
    node: NodeRef | None = Field(default=None, description="syntax node the annotation occupies")
