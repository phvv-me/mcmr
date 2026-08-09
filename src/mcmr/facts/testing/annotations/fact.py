from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .annotation import TypeAnnotation


class TypeAnnotationFact(Fact):
    """Describe one resolved type annotation."""

    annotations: list[TypeAnnotation] = Field(
        default=[], description="resolved annotations this file declares"
    )
