from enum import StrEnum, auto

import polars as pl

from ..... import Category, rule
from .....domain.contracts import Criterion
from .....execution import ClassificationBackend, CriterionValue
from .....execution.queries import AssessmentContract, ModelQuery
from .....facts import FunctionFact
from .....table import FunctionRelation, Table


class PrimitiveObsession(StrEnum):
    APPROPRIATE = auto()
    VALUE_OBJECT = auto()
    DOMAIN_MODEL = auto()
    MODELED = auto()
    OVERMODELED = auto()
    UNCERTAIN = auto()


_DOMAIN_RULES_REPEAT = "domain rules repeat"
_ONE_VALUE_OWNS_MEANING = "one value owns meaning"
_VALUES_CHANGE_TOGETHER = "values change together"
_EXISTING_MODEL_OWNS_RULES = "existing model owns rules"
_GENERIC_FORM_REQUIRED = "generic form required"
_CRITERIA = (
    Criterion(
        name=_DOMAIN_RULES_REPEAT,
        question="Do stable validation, units, states, or operations repeat?",
    ),
    Criterion(
        name=_ONE_VALUE_OWNS_MEANING,
        question="Does one generic value carry the repeated domain meaning?",
    ),
    Criterion(
        name=_VALUES_CHANGE_TOGETHER,
        question="Do several values participate in one state transition?",
    ),
    Criterion(
        name=_EXISTING_MODEL_OWNS_RULES,
        question="Does an existing wrapper centralize the domain rules?",
    ),
    Criterion(
        name=_GENERIC_FORM_REQUIRED,
        question="Is the generic representation required by a local or external boundary?",
    ),
)
_TABLE = (
    (
        PrimitiveObsession.MODELED,
        (
            (_DOMAIN_RULES_REPEAT, CriterionValue.YES),
            (_EXISTING_MODEL_OWNS_RULES, CriterionValue.YES),
        ),
    ),
    # A required generic form settles this before any row about a wrapper does, since a value
    # something outside forces to stay generic says nothing about modeling too much.
    (PrimitiveObsession.APPROPRIATE, ((_GENERIC_FORM_REQUIRED, CriterionValue.YES),)),
    (
        PrimitiveObsession.OVERMODELED,
        (
            (_DOMAIN_RULES_REPEAT, CriterionValue.NO),
            (_EXISTING_MODEL_OWNS_RULES, CriterionValue.YES),
        ),
    ),
    (
        PrimitiveObsession.APPROPRIATE,
        (
            (_DOMAIN_RULES_REPEAT, CriterionValue.NO),
            (_EXISTING_MODEL_OWNS_RULES, CriterionValue.NO),
        ),
    ),
    (
        PrimitiveObsession.DOMAIN_MODEL,
        (
            (_DOMAIN_RULES_REPEAT, CriterionValue.YES),
            (_VALUES_CHANGE_TOGETHER, CriterionValue.YES),
        ),
    ),
    (
        PrimitiveObsession.VALUE_OBJECT,
        (
            (_DOMAIN_RULES_REPEAT, CriterionValue.YES),
            (_ONE_VALUE_OWNS_MEANING, CriterionValue.YES),
        ),
    ),
)


@rule(
    "ALL-DESI1001",
    policy=Category.outcomes(
        good={
            "appropriate",
            "domain_model",
            "modeled",
            "value_object",
        },
        neutral={"uncertain"},
    ),
)
def primitive_obsession(
    subject: Table[FunctionFact],
    backend: ClassificationBackend,
) -> ModelQuery[PrimitiveObsession]:
    """Classify whether generic values hide repeated domain rules.

    Definition
    ----------
    A primitive is a generic value such as `str`, `int`, or `dict`. Using one is normal. The Fowler
    smell appears only when repeated validation, units, legal states, or operations give that value
    stable domain meaning. One value with repeated rules suggests a value object. Several values
    that change state together suggest a domain model. An existing wrapper is useful only when it
    centralizes those rules. The final category is selected by the explicit decision table, not by
    the judgment backend.

    Evidence
    --------
    Each finding names one independently assessed predicate and the exact retained claims behind
    it, so a reader can check the deterministic result against evidence rather than against the
    model. Those claims cite repeated validation sites, operations, parameter groups, state
    transitions, call boundaries, and any existing wrapper. A proposed class is not evidence that
    an existing abstraction adds knowledge. The repair is always a choice here, because a judgment
    nobody can reproduce is not an edit.

    Exceptions
    ----------
    Local counters, transient parsing values, stable wire formats, and framework-required scalar
    fields can remain generic when their domain rules are not duplicated. A required generic form
    is read before any existing wrapper is weighed, so building a domain type out of the raw values
    a boundary hands over is `appropriate` rather than one model too many.

    Examples
    --------
    .. rubric:: Bad example

    Validation for the same monetary concept is repeated at several boundaries.

    .. code-block:: python

       def charge(amount_minor: int, currency: str) -> None:
           if amount_minor < 0 or currency not in SUPPORTED_CURRENCIES:
               raise ValueError("invalid money")

    .. rubric:: Good example

    One immutable value owns the invariant and reusable operation.

    .. code-block:: python

       class Money(FrozenModel):
           amount_minor: int
           currency: Currency

           def add(self, other: Money) -> Money:
               if self.currency is not other.currency:
                   raise ValueError("currency mismatch")
               return Money(
                   amount_minor=self.amount_minor + other.amount_minor,
                   currency=self.currency,
               )

    A loop counter that never crosses its local algorithm remains an `int`.

    References
    ----------
    Cites "Refactoring", Primitive Obsession
    Cites "Domain-Driven Design", Value Objects
    Cites "Refactoring Guru", primitive obsession smell
    """
    query = backend.assessment(
        subject,
        contract=AssessmentContract(
            criteria=list(_CRITERIA),
            instructions=primitive_obsession.instructions,
            decision_table=_TABLE,
            default=PrimitiveObsession.UNCERTAIN,
            uncertain=PrimitiveObsession.UNCERTAIN,
        ),
    )
    if subject.relation_type is FunctionRelation:
        primitive = (
            subject.lazy(FunctionRelation.PARAMETERS)
            .filter(
                ~pl.col("is_receiver")
                & pl.col("type_name").str.contains(
                    r"(?i)^(?:str|string|bool|boolean|int|integer|u?int\d*|i\d+|float|"
                    r"f32|f64|dict|map|list|vec|set|tuple|array)$"
                )
            )
            .group_by("function_id", maintain_order=True)
            .len(name="primitive_parameter_count")
            .filter(pl.col("primitive_parameter_count") >= 2)
        )
        selected = (
            subject.lazy(FunctionRelation.FUNCTIONS)
            .filter((pl.col("conditional_count") > 0) & ~pl.col("is_test"))
            .join(primitive, left_on="entity_id", right_on="function_id", how="semi")
            .select("fact_id")
        )
        query = query.matching(selected)
    else:
        query = query.where(
            (pl.col("parameters.length") >= 2)
            & (pl.col("conditional_count") > 0)
            & ~pl.col("is_test")
        )
    return query.choice(
        question="check `{value}` against the sites those claims name",
        options=(
            "model the value where the rules really do repeat",
            "leave it generic where each site means something different",
        ),
    )
