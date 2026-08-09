from pydantic import Field

from ...foundation import Fact


class TestSuiteFact(Fact):
    """Describe one test suite and its collected execution evidence."""

    strict_controls: dict[str, bool] = Field(
        default={},
        description="whether pytest enforces each strict control, such as strict_markers",
    )
    import_mode: str = Field(
        default="prepend", description="pytest's configured import mode for collecting tests"
    )
    anyio_mode: str = Field(
        default="", description="pytest-anyio mode configured in ini_options, empty when unset"
    )
    asyncio_mode: str = Field(
        default="", description="pytest-asyncio mode configured in ini_options, empty when unset"
    )
    is_coverage_configured: bool = Field(
        default=False, description="whether pytest's addopts pass --cov"
    )
    is_branch_coverage_enabled: bool = Field(
        default=False, description="whether tool.coverage.run sets branch coverage on"
    )
