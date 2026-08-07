from typing import TYPE_CHECKING, Literal, Self

from patos import FrozenModel
from pydantic import model_validator

from .contracts import Policy, Verdict
from .kinds import PolicyKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..contracts import RuleValue


class PolicyDecisions:
    """Own the closed acceptance policies available to rule definitions."""

    class Boolean(Policy):
        """Require one exact Boolean value."""

        kind: Literal[PolicyKind.BOOLEAN] = PolicyKind.BOOLEAN
        expected: bool = False

        def verdict(self, value: RuleValue) -> Verdict:
            """Return whether the occurrence matched the expected Boolean."""
            if not isinstance(value, bool):
                return Verdict.UNASSESSED
            return Verdict.PASS if value is self.expected else Verdict.FAIL

    class Category(Policy):
        """Map every meaningful category to a good, neutral, or bad outcome."""

        kind: Literal[PolicyKind.CATEGORY] = PolicyKind.CATEGORY
        good: set[str] = set()
        neutral: set[str] = set()
        bad: set[str] = set()

        @staticmethod
        def advisory() -> PolicyDecisions.Outcomes:
            """Declare that every category this rule may answer is advice rather than a verdict."""
            return PolicyDecisions.Outcomes(neutral=None)

        @staticmethod
        def outcomes(
            *,
            good: Iterable[str] = (),
            neutral: Iterable[str] = (),
        ) -> PolicyDecisions.Outcomes:
            """Declare the categories this project accepts and tolerates, leaving the rest bad."""
            return PolicyDecisions.Outcomes(
                good={str(item) for item in good},
                neutral={str(item) for item in neutral},
            )

        @model_validator(mode="after")
        def partition(self) -> Self:
            """Require one nonempty partition with no category assigned twice."""
            buckets = [self.good, self.neutral, self.bad]
            if not any(buckets):
                raise ValueError("a category policy needs at least one category")
            if sum(map(len, buckets)) != len(self.good | self.neutral | self.bad):
                raise ValueError("good, neutral, and bad categories must be disjoint")
            return self

        def verdict(self, value: RuleValue) -> Verdict:
            """Return the declared outcome for one category."""
            if not isinstance(value, str):
                return Verdict.UNASSESSED
            if value in self.good:
                return Verdict.PASS
            if value in self.bad:
                return Verdict.FAIL
            return Verdict.UNASSESSED

    class Outcomes(FrozenModel):
        """Name what one rule accepts and tolerates before its answer enum is known.

        A rule's return annotation already states the closed answer set, so a declaration repeats
        neither the enum nor the categories it rejects. `closed` completes the partition from that
        annotation, and a `neutral` of `None` tolerates every answer the rule may give.
        """

        good: set[str] = set()
        neutral: set[str] | None = set()

        def closed(self, rule_id: str, categories: Iterable[str]) -> PolicyDecisions.Category:
            """Complete this declaration against the answer set one return annotation states."""
            answers = set(categories)
            if self.neutral is None:
                return PolicyDecisions.Category(neutral=answers)
            if unknown := sorted((self.good | self.neutral) - answers):
                raise ValueError(f"{rule_id} policy names absent categories {', '.join(unknown)}")
            return PolicyDecisions.Category(
                good=self.good,
                neutral=self.neutral,
                bad=answers - self.good - self.neutral,
            )

    class Numeric(Policy):
        """Require a numeric value inside one closed interval."""

        kind: Literal[PolicyKind.NUMERIC] = PolicyKind.NUMERIC
        minimum: float | None = None
        maximum: float | None = None

        @model_validator(mode="after")
        def ordered(self) -> Self:
            """Reject an interval whose lower bound exceeds its upper bound."""
            if (
                self.minimum is not None
                and self.maximum is not None
                and self.minimum > self.maximum
            ):
                raise ValueError("minimum cannot exceed maximum")
            return self

        def verdict(self, value: RuleValue) -> Verdict:
            """Return whether one measurement falls inside the interval."""
            if isinstance(value, str | bool):
                return Verdict.UNASSESSED
            below = self.minimum is not None and value < self.minimum
            above = self.maximum is not None and value > self.maximum
            return Verdict.FAIL if below or above else Verdict.PASS


Boolean = PolicyDecisions.Boolean
Category = PolicyDecisions.Category
Numeric = PolicyDecisions.Numeric
Outcomes = PolicyDecisions.Outcomes
