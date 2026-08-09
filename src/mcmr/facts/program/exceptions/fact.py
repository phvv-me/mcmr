from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .usage import ExceptionUsage


class ExceptionFact(Fact):
    """Describe one exception declaration and its uses."""

    exceptions: list[ExceptionUsage] = Field(
        default=[], description="project exception classes this module declares"
    )
