from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .model import PydanticModelAnalysis


class PydanticModelFact(Fact):
    """Describe one Pydantic model and its validation contract."""

    models: list[PydanticModelAnalysis] = Field(
        default=[], description="model class candidates this fact analyzes"
    )
