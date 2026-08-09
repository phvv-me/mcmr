from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr
from ...foundation import SourceSpan


class TypingDefinition(FrozenModel):
    """Locate one reusable typing declaration."""

    name: NonEmptyStr = Field(description="name of the reusable typing declaration")
    span: SourceSpan = Field(description="source location where the typing declaration is defined")
