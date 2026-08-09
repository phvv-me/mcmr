from patos import FrozenModel
from pydantic import Field

from .....domain.primitives import NonEmptyStr


class SecurityBoundaryFields(FrozenModel):
    """Retain boundary identity, scope, assets, flows, actors, threats, and mitigations."""

    name: NonEmptyStr = Field(description="boundary name")
    in_scope: bool = Field(
        default=True, description="whether the boundary counts toward threat model coverage"
    )
    assets: list[str] = Field(default=[], description="assets the boundary protects")
    flows: list[str] = Field(default=[], description="data or trust flows crossing the boundary")
    actors: list[str] = Field(default=[], description="actors that can act across the boundary")
    threats: list[str] = Field(default=[], description="threats identified against the boundary")
    mitigations: list[str] = Field(
        default=[], description="mitigations declared for the identified threats"
    )
