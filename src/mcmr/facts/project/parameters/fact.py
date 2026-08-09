from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .use import ParameterUse


class ParameterFact(Fact):
    """Describe one callable parameter and its uses."""

    parameters: list[ParameterUse] = Field(
        default=[], description="annotated parameters this fact retains with their resolved uses"
    )
