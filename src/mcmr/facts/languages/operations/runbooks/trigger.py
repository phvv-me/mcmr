from pydantic import Field

from .groups import RunbookTriggerFields


class RunbookTrigger(RunbookTriggerFields):
    """Retain one operational trigger and evidence its guidance remains usable."""

    design_evidence: str = Field(
        default="", description="evidence the self-healing design has been reviewed or proven"
    )
