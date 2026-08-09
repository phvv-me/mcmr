from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .flag import FeatureFlag


class FeatureFlagFact(Fact):
    """Describe one feature flag and its lifecycle evidence."""

    flags: list[FeatureFlag] = Field(default=[], description="feature flags this fact retains")
