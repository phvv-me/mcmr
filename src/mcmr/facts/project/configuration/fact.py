from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .assignment import ConfigurationAssignment
    from .python import PythonTargetConfiguration


class ProjectConfigurationFact(Fact):
    """Describe one project configuration source."""

    assignments: list[ConfigurationAssignment] = Field(
        default=[], description="literal collection assignments this configuration source declares"
    )
    python_target: PythonTargetConfiguration | None = Field(
        default=None, description="Python version target this project and its tools declare"
    )
