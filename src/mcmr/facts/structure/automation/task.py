from patos import FrozenModel
from pydantic import Field


class AutomationTask(FrozenModel):
    """Describe one repository-owned command for a lifecycle capability."""

    capability: str = Field(
        description="lifecycle capability the task automates, e.g. setup or test"
    )
    commands: list[str] = Field(
        default=[], description="declared commands resolving this capability"
    )
    guidance_locations: list[str] = Field(
        default=[], description="documentation files that mention how to invoke this capability"
    )
    is_repository_owned: bool = Field(
        default=True,
        description="whether every command stays inside the checkout instead of the host machine",
    )
    is_noninteractive: bool = Field(
        default=True,
        description="whether every command completes without a person at the terminal",
    )
