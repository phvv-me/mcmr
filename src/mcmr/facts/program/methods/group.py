from patos import FrozenModel
from pydantic import Field


class MethodCloneGroup(FrozenModel):
    """Retain exact sibling method definitions sharing a meaningful base."""

    normalized_definition: str = Field(
        description="method name, parameter count, and body normalized for exact comparison"
    )
    locations: list[str] = Field(
        default=[], description="path and line locations where this normalized definition occurs"
    )
    direct_base: str = Field(description="qualified name of the class's shared direct base")
