from patos import FrozenModel
from pydantic import Field

from ...foundation import SourceSpan


class ParameterUseFields(FrozenModel):
    """Retain parameter name, owner, source span, and annotation."""

    name: str = Field(default="", description="name of the annotated parameter")
    owner: str = Field(default="", description="name of the function that declares the parameter")
    span: SourceSpan | None = Field(
        default=None, description="source range the parameter declaration occupies"
    )
    annotation: str = Field(description="type annotation text the parameter declares")
