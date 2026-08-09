from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .operation import QueryOperation


class QueryFact(Fact):
    """Describe one resolved database query."""

    operations: list[QueryOperation] = Field(
        default=[], description="resolved SQLAlchemy or SQLModel operations this fact retains"
    )
