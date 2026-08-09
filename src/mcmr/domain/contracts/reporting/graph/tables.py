from patos import FrozenModel


class RuleTables(FrozenModel):
    """State the fact tables one rule declared and the one its verdicts anchor on.

    A rule names every family it reads, and one of those families is what the rule is really
    about, which is where a verdict about ordinary source has to be stored. The two travel
    together because a reader asking what a rule reads is asking both halves of one question.
    """

    inputs: list[str] = []
    primary: str = ""
