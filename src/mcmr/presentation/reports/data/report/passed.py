from patos import FrozenModel


class RulePass(FrozenModel):
    """Retain one selected rule that observed the repository and found nothing to report."""

    rule: str
    callable: str = ""
    summary: str
