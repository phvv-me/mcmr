from patos import FrozenModel
from pydantic import Field

from .....domain.primitives import NonEmptyStr


class ServiceObjectiveFields(FrozenModel):
    """Retain service identity, scope, ownership, and objective evidence."""

    name: NonEmptyStr = Field(description="service name")
    in_scope: bool = Field(
        default=True, description="whether the service counts toward objective coverage"
    )
    user_facing: bool = Field(
        default=True, description="whether the service serves end users directly"
    )
    owner: str = Field(
        default="", description="team or person accountable for the service, empty when unassigned"
    )
    user_journeys: list[str] = Field(
        default=[], description="user journeys the service level objective is meant to protect"
    )
    indicators: list[str] = Field(
        default=[], description="service level indicators tracked for the service"
    )
    objectives: list[str] = Field(
        default=[], description="target values declared for each tracked indicator"
    )
