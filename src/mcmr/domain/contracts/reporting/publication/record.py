from .groups import RunRecordFields


class RunRecord(RunRecordFields.Estimate):
    """State what one rule concluded about one governed subject in one completed run.

    A record is what a later run compares itself against, so it carries the verdict, the
    measurement behind it, and how far the repair got, rather than a rendered sentence.
    """

    @property
    def properties(self) -> dict[str, str]:
        """Return the flat key and value pairs a receiving system stores beside the verdict."""
        stated = {
            "rule": self.rule,
            "lane": self.lane,
            "path": self.path,
            "measurement": self.measurement,
            "findings": str(self.finding_count),
            "repair": str(self.repair),
            "reasons": " | ".join(self.reasons),
            "reasoning": self.reasoning,
            "confidence": "" if self.confidence is None else f"{self.confidence:.2f}",
        } | self.spend.properties
        return {name: value for name, value in stated.items() if value}
