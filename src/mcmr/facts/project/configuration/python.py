from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class PythonTargetConfiguration(FrozenModel):
    """Retain the Python minor accepted by the project and configured tools."""

    project_minimum_minor: NonNegativeInt | None = Field(
        default=None, description="minimum Python 3 minor version requires-python declares"
    )
    configured_tools: list[str] = Field(
        default=[], description="names of tool tables that declare their own Python version target"
    )
    tool_target_minors: dict[str, NonNegativeInt] = Field(
        default={}, description="Python 3 minor version each configured tool targets, by tool name"
    )
    per_file_target_minors: list[NonNegativeInt] = Field(
        default=[], description="Python 3 minor version Ruff assigns per file pattern override"
    )
