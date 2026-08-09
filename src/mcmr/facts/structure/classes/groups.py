from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ...foundation import MemberKind, SourceSpan, Visibility


class MethodAnalysisFields(FrozenModel):
    """Retain method identity, source, region, kind, visibility, and decorators."""

    name: str = Field(description="name the method declares")
    span: SourceSpan = Field(description="source range the method declaration occupies")
    source: str = Field(default="", description="verbatim source text of the method declaration")
    region: NonNegativeInt = Field(
        default=0, description="index of the `# region` marked section the method sits under"
    )
    kind: MemberKind = Field(
        default=MemberKind.METHOD, description="what kind of type member the method declares"
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        description="how widely the method name is exposed, derived from its naming convention",
    )
    decorators: list[str] = Field(
        default=[], description="literal source text of each decorator applied to the method"
    )
