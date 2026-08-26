from pydantic import Field, NonNegativeInt

from .place import ManuscriptPlace


class ManuscriptStatement(ManuscriptPlace):
    """Retain one numbered statement and whatever followed it."""

    kind: str = Field(default="", description="environment name the document declared it under")
    label: str = Field(default="", description="cross reference target this statement declares")
    owes_proof: bool = Field(
        default=False, description="whether the declaring theorem style asserts rather than names"
    )
    close_order: NonNegativeInt = Field(
        default=0, description="reading order at which this statement's environment closed"
    )
    proof_order: NonNegativeInt = Field(
        default=0, description="reading order of an adjacent proof environment, zero when none"
    )
    discharge_head: str = Field(
        default="", description="opening words of the prose immediately following the statement"
    )
    word_count: NonNegativeInt = Field(default=0, description="prose words the statement holds")
