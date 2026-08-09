from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from .....domain.primitives import NonEmptyStr
from ..states.project import DependencyProjectState
from ..states.release import DependencyReleaseState
from ..states.repository import DependencyRepositoryState


class DependencyRecordFields(FrozenModel):
    """Retain release identity, dates, version, and standardized states."""

    name: NonEmptyStr = Field(description="name of the dependency package")
    resolved_release_day: NonNegativeInt | None = Field(
        default=None,
        description="day-resolution timestamp of the exact release currently resolved",
    )
    latest_compatible_release_day: NonNegativeInt | None = Field(
        default=None,
        description="day-resolution timestamp of the latest compatible release",
    )
    latest_compatible_version: NonEmptyStr | None = Field(
        default=None, description="version of the latest release compatible with the requirement"
    )
    project_state: DependencyProjectState = Field(
        default=DependencyProjectState.UNKNOWN,
        description="standardized publication state of the dependency project",
    )
    repository_state: DependencyRepositoryState = Field(
        default=DependencyRepositoryState.UNKNOWN,
        description="standardized archive state of the dependency's source repository",
    )
    resolved_release_state: DependencyReleaseState = Field(
        default=DependencyReleaseState.UNKNOWN,
        description="standardized yank state of the exact resolved release",
    )
