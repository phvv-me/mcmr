from enum import StrEnum, auto

from ...... import Category, rule
from ......domain.contracts import Criterion
from ......execution import ClassificationBackend, CriterionValue
from ......execution.queries import AssessmentContract, ModelQuery
from ......facts import DeploymentFact
from ......table import Table


class ProgressiveRollout(StrEnum):
    VERIFIED = auto()
    PARTIAL = auto()
    UNSAFE = auto()
    NOT_NEEDED = auto()
    UNCERTAIN = auto()


_PROGRESSIVE_ROLLOUT_NEEDED = "progressive rollout needed"
_EXPOSURE_IS_STAGED = "exposure is staged"
_STAGE_IS_REPRESENTATIVE = "stage is representative"
_OUTCOMES_DECIDE = "outcomes decide"
_RECOVERY_WORKS = "recovery works"
_CRITERIA = (
    Criterion(name=_PROGRESSIVE_ROLLOUT_NEEDED, question="Does this change need staged exposure?"),
    Criterion(name=_EXPOSURE_IS_STAGED, question="Is broad exposure preceded by a bounded stage?"),
    Criterion(
        name=_STAGE_IS_REPRESENTATIVE, question="Does the stage represent the risk population?"
    ),
    Criterion(
        name=_OUTCOMES_DECIDE, question="Are attributable outcomes compared with thresholds?"
    ),
    Criterion(
        name=_RECOVERY_WORKS, question="Can the rollout halt or recover when thresholds fail?"
    ),
)
_TABLE = (
    (
        ProgressiveRollout.NOT_NEEDED,
        ((_PROGRESSIVE_ROLLOUT_NEEDED, CriterionValue.NO),),
    ),
    (
        ProgressiveRollout.UNSAFE,
        (
            (_PROGRESSIVE_ROLLOUT_NEEDED, CriterionValue.YES),
            (_EXPOSURE_IS_STAGED, CriterionValue.NO),
        ),
    ),
    (
        ProgressiveRollout.UNSAFE,
        (
            (_PROGRESSIVE_ROLLOUT_NEEDED, CriterionValue.YES),
            (_STAGE_IS_REPRESENTATIVE, CriterionValue.NO),
        ),
    ),
    (
        ProgressiveRollout.UNSAFE,
        (
            (_PROGRESSIVE_ROLLOUT_NEEDED, CriterionValue.YES),
            (_RECOVERY_WORKS, CriterionValue.NO),
        ),
    ),
    (
        ProgressiveRollout.VERIFIED,
        [(criterion.name, CriterionValue.YES) for criterion in _CRITERIA],
    ),
)


@rule(
    "ALL-DEPL1001",
    policy=Category.outcomes(good={"not_needed", "verified"}, neutral={"uncertain"}),
)
def progressive_rollout(
    subject: Table[DeploymentFact],
    backend: ClassificationBackend,
) -> ModelQuery[ProgressiveRollout]:
    """Judge whether a risky deployment verifies behavior before broad exposure.

    Definition
    ----------
    Ask the selected judgment backend for five independently cited rollout facts and reduce them
    through a fixed decision table. The model never chooses the final category. Compare change
    exposure, stage representativeness, attributable outcomes, decision thresholds, and recovery.

    Evidence
    --------
    The frozen bundle cites rollout configuration, populations, signals, comparisons, thresholds,
    observation windows, and recovery actions. Missing, duplicate, conflicting, or uncited model
    answers remain `unknown` and reduce to `uncertain`.

    Exceptions
    ----------
    Low-risk offline artifacts may not need progressive exposure when equivalent verification
    covers the complete risk.

    Examples
    --------
    A representative canary compared with a control and protected by rollback is `verified`.
    Sending traffic to an unrepresentative stage without recovery is `unsafe`.

    References
    ----------
    Cites "The Site Reliability Workbook", Canarying Releases
    Cites "Accelerate", continuous delivery
    Cites "Release It", stability patterns
    """
    return backend.assessment(
        subject,
        contract=AssessmentContract(
            criteria=list(_CRITERIA),
            instructions=progressive_rollout.instructions,
            decision_table=_TABLE,
            default=ProgressiveRollout.PARTIAL,
            uncertain=ProgressiveRollout.UNCERTAIN,
        ),
    )
