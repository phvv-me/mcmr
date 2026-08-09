from pydantic import Field

from .groups import AlertDefinitionFields


class AlertDefinition(AlertDefinitionFields):
    """Retain the configured fields one responder receives from an alert."""

    destination: str = Field(default="", description="paging target the alert notifies")
    action: str = Field(default="", description="expected first response action for the alert")
    runbook: str = Field(default="", description="link or path to the runbook for the alert")
    recent_outcomes: list[str] = Field(
        default=[], description="outcomes recorded from the alert's most recent firings"
    )
