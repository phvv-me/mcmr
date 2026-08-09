from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class ConditionalArm(FrozenModel):
    """Retain one conditional arm and its selecting comparison."""

    comparison: str = Field(
        default="", description="kind of comparison the arm's test performs against the subject"
    )
    literal: str = Field(
        default="",
        description="literal text the arm compares the subject to, empty when the arm reads "
        "wider state",
    )
    statement_count: NonNegativeInt = Field(
        default=0, description="number of statements in the arm's body"
    )
    returns_value: bool = Field(
        default=False, description="whether the arm's last statement returns a value"
    )
    reads_subject_only: bool = Field(
        default=True, description="whether the arm's test reads only the chain's subject"
    )
