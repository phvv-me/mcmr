from typing import TYPE_CHECKING

from pydantic import Field

from .protected import ProtectedRegion

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from .handler import ExceptionHandler


class ExceptionRegion(ProtectedRegion):
    """Retain protected setup and executable clause sizes for one try statement."""

    clause_statement_counts: list[NonNegativeInt] = Field(
        default=[], description="statement count of each except clause, in source order"
    )
    handlers: list[ExceptionHandler] = Field(
        default=[], description="except clauses this try statement declares"
    )
    has_else: bool = Field(
        default=False, description="whether the try statement carries an else clause"
    )
    has_finally: bool = Field(
        default=False, description="whether the try statement carries a finally clause"
    )
    is_exception_group: bool = Field(
        default=False,
        description="whether the try statement catches with except* rather than except",
    )
