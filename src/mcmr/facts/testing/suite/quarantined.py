from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class QuarantinedTest(FrozenModel):
    """Retain one quarantined test and its remediation evidence."""

    name: str = Field(description="name of the quarantined test function")
    age_days: NonNegativeInt | None = Field(
        default=None,
        description="days since the quarantine marker's since date, unknown when unset",
    )
    owner: str = Field(
        default="", description="owner named on the quarantine marker, empty when none"
    )
    has_remediation_evidence: bool = Field(
        default=False, description="whether the quarantine marker states a remediation note"
    )
    recurred_after_repair: bool = Field(
        default=False,
        description="whether the quarantine marker states the flake recurred after repair",
    )
