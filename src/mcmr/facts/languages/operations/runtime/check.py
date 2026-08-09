from patos import FrozenModel
from pydantic import Field


class RuntimeTypeCheck(FrozenModel):
    """Retain a concrete type check and its guarded operations."""

    concrete_type: str = Field(description="type name passed as the second argument to isinstance")
    guarded_operations: list[str] = Field(
        default=[],
        description="operations and attributes the guarded block performs on the checked value",
    )
    can_use_eafp: bool = Field(
        default=False,
        description="whether the branch does nothing but the guarded operation, so try/except "
        "would work as well",
    )
