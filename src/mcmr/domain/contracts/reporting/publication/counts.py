from patos import FrozenModel
from pydantic import NonNegativeInt


class RuleCounts(FrozenModel):
    """State how many rules one whole invocation activated and how many came back failing.

    A run is wide or narrow before it is clean or dirty, and the lane breakdown is what says what
    kind of work it actually did, so the three numbers answer one question together rather than
    three questions a reader has to assemble.
    """

    executed: NonNegativeInt = 0
    failing: NonNegativeInt = 0
    by_lane: dict[str, NonNegativeInt] = {}
