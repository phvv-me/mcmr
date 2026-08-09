from patos import FrozenModel
from pydantic import NonNegativeFloat, NonNegativeInt

from ..graph import ModelSpend
from .counts import RuleCounts


class RunSummary(FrozenModel):
    """State how much one whole invocation reached, beside the verdicts it reached them with.

    A verdict says what one rule concluded about one subject. This says what the run itself did,
    which is the question a run history answers and a rule timeline never can, so a reader can
    tell a wide cheap run from a narrow expensive one without opening either.
    """

    files: NonNegativeInt = 0
    facts: NonNegativeInt = 0
    failures: NonNegativeInt = 0
    findings: NonNegativeInt = 0
    rules: RuleCounts = RuleCounts()
    duration_milliseconds: NonNegativeFloat = 0.0
    spend: ModelSpend = ModelSpend()

    @property
    def properties(self) -> dict[str, str]:
        """Return the flat key and value pairs a receiving system stores beside the run."""
        stated = {
            "files": str(self.files),
            "facts": str(self.facts),
            "failures": str(self.failures),
            "findings": str(self.findings),
            "rulesExecuted": str(self.rules.executed),
            "rulesFailing": str(self.rules.failing),
            "durationMillis": str(round(self.duration_milliseconds)),
        }
        lanes = {
            f"rules{lane.capitalize()}": str(count)
            for lane, count in sorted(self.rules.by_lane.items())
        }
        return stated | lanes | self.spend.properties
