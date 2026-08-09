from pydantic import Field

from .groups import ChangeRecordFields


class ChangeRecord(ChangeRecordFields):
    """Retain one change and the review policy applied by its merge path."""

    verification_evidence: list[str] = Field(
        default=[], description="recorded evidence verifying a mechanical change"
    )
