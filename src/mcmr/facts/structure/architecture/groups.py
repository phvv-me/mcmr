from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr


class ArchitectureFields(FrozenModel):
    """Retain architecture quality name, objective, check, and result."""

    name: NonEmptyStr = Field(description="name of the declared architecture quality")
    objective: str = Field(default="", description="stated target the characteristic must meet")
    check: str = Field(
        default="", description="executable or repeatable check that verifies the objective"
    )
    retained_result: str = Field(
        default="", description="last recorded outcome of running the check"
    )
