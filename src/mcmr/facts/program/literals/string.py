from patos import FrozenModel
from pydantic import Field, PositiveInt


class StringLiteralGroup(FrozenModel):
    """Retain exact equal strings sharing one resolved syntax role."""

    value: str = Field(description="exact string literal value repeated across occurrences")
    role: str = Field(
        description="resolved syntax role the literal occupies, such as value, argument, "
        "keyword, or comparison"
    )
    occurrence_count: PositiveInt = Field(
        description="number of times the value occurs in this role"
    )
    files: list[str] = Field(
        default=[], description="repository relative paths where the value occurs in this role"
    )
    is_excluded_vocabulary: bool = Field(
        default=False,
        description="whether the role is a bare value the module states directly rather than a "
        "resolved cross-file decision",
    )
    is_callee_vocabulary: bool = Field(
        default=False,
        description="whether the role hands the value to a callable as an argument or keyword",
    )
