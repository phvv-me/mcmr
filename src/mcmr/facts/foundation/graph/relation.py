from patos import FrozenModel
from pydantic import Field


class Relation(FrozenModel):
    """Relate two named units in one repository vocabulary."""

    source: str = Field(description="name of the referencing unit in the relation")
    target: str = Field(description="name of the referenced unit in the relation")
