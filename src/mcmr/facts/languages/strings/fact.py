from typing import Annotated

from pydantic import Field

from ...foundation import Fact
from .literal import LiteralStringExpression
from .repeated import RepeatedStringExpression

type StringExpressionValue = Annotated[
    LiteralStringExpression | RepeatedStringExpression,
    Field(discriminator="kind"),
]


class StringExpressionFact(Fact):
    """Describe every literal and fixed repetition producing a string."""

    expressions: list[StringExpressionValue] = Field(
        default=[], description="literal and fixed-repetition string expressions this file folds"
    )
