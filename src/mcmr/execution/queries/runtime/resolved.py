from patos import FrozenModel, Runtime

from ....domain.contracts import ModelSpend, RuleValue
from ....query import RuleQuery


class ResolvedQuery(FrozenModel):
    """Retain the relational answers one contextual query produced beside what they cost.

    Only a failing rule keeps its findings, and the model was paid for whichever way the rule
    answered, so the spend travels beside the answers rather than inside them.
    """

    query: Runtime[RuleQuery[RuleValue]]
    spend: dict[str, ModelSpend] = {}
