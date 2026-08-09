from typing import TYPE_CHECKING

from pydantic import Field

from ....foundation import Fact

if TYPE_CHECKING:
    from .workflow import CIWorkflow


class CIConfigurationFact(Fact):
    """Describe one continuous integration configuration."""

    workflows: list[CIWorkflow] = Field(
        default=[], description="continuous integration workflows this fact retains"
    )
