from typing import Literal

from patos import FrozenModel
from pydantic import Field, PositiveInt


class LifetimeAnnotationFields(FrozenModel):
    """Retain lifetime identity, source position, and signature evidence."""

    owner: str = Field(description="name of the declaration the annotation belongs to")
    kind: Literal["function", "method", "type", "trait", "alias"] = Field(
        description="shape of the declaration naming the lifetime"
    )
    names: list[str] = Field(default=[], description="lifetime names the declaration states")
    line: PositiveInt = Field(default=1, description="line the declaration is stated on")
    returned: list[str] = Field(default=[], description="lifetime names the return type states")
    receiver: str = Field(
        default="", description="lifetime name the self receiver carries, empty when none"
    )
    parameters: list[str] = Field(
        default=[], description="lifetime names the non-receiver parameters state"
    )
