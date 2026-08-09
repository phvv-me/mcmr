from typing import Literal

from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr


class AlertDefinitionFields(FrozenModel):
    """Retain alert identity, audience, condition, severity, impact, and owner."""

    name: NonEmptyStr = Field(description="alert's display name")
    enabled: bool = Field(default=True, description="whether the alert is currently active")
    audience: Literal["paging", "informational"] = Field(
        default="paging", description="whether the alert pages a responder or is informational"
    )
    condition: str = Field(
        default="", description="condition or threshold that triggers the alert"
    )
    severity: str = Field(default="", description="declared severity level of the alert")
    impact: str = Field(default="", description="what breaks or degrades when the alert fires")
    owner: str = Field(
        default="", description="team or person accountable for responding to the alert"
    )
