from patos import FrozenModel
from pydantic import Field, NonNegativeFloat

from ....foundation import Ratio


class CICheck(FrozenModel):
    """Describe one CI check and its measured duration percentile."""

    name: str = Field(description="name of the CI check")
    duration_percentile_seconds: NonNegativeFloat = Field(
        description="measured duration of the check at the configured percentile"
    )
    percentile: Ratio = Field(
        default=0.9, description="point of the check's duration distribution this measures"
    )
    is_required: bool = Field(default=True, description="whether the check must pass")
    is_change_blocking: bool = Field(
        default=True, description="whether the check blocks merging a change"
    )
