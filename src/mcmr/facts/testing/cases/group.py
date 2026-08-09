from patos import FrozenModel
from pydantic import Field


class TestCaseGroup(FrozenModel):
    """Retain sibling tests with the same normalized nonliteral syntax."""

    normalized_syntax: str = Field(
        description="test body with every literal replaced by a placeholder"
    )
    literal_vectors: list[list[str]] = Field(
        default=[], description="literal values each sibling test stated, in source order"
    )
