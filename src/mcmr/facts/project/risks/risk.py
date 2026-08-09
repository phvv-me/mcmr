from patos import FrozenModel
from pydantic import Field

from ....domain.primitives import NonEmptyStr


class OperationalRisk(FrozenModel):
    """Retain one failure concern before contextual assessment."""

    name: NonEmptyStr = Field(description="name identifying the operational risk")
    critical_path: str = Field(
        default="", description="user journey or workflow the risk threatens"
    )
    failure_modes: list[str] = Field(
        default=[], description="ways the critical path can fail that the risk names"
    )
    diagnostic_questions: list[str] = Field(
        default=[], description="questions telemetry needs to answer to distinguish a failure mode"
    )
    signals: list[str] = Field(
        default=[], description="telemetry signals retained to answer the diagnostic questions"
    )
    owner: str = Field(default="", description="team or person accountable for the risk")
