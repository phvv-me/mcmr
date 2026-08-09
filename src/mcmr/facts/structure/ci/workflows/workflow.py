from patos import FrozenModel
from pydantic import Field


class CIWorkflow(FrozenModel):
    """Describe one parsed workflow and its protections."""

    name: str = Field(description="name of the parsed workflow")
    tasks: list[str] = Field(
        default=[], description="task or job names the workflow runs, e.g. lint or test"
    )
    triggers: list[str] = Field(
        default=[], description="events that start the workflow, e.g. pull_request"
    )
    is_change_blocking: bool = Field(
        default=False, description="whether the workflow blocks merging a change"
    )
    uses_locked_dependencies: bool = Field(
        default=True,
        description="whether the workflow installs dependencies from a locked version set",
    )
    has_explicit_permissions: bool = Field(
        default=True, description="whether the workflow declares explicit permissions"
    )
    cancels_superseded_runs: bool = Field(
        default=True,
        description="whether a new push cancels the workflow's stale in-flight run",
    )
