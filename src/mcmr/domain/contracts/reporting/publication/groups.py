from typing import Annotated

from annotated_types import Ge, Le
from patos import FrozenModel

from ....primitives import NonEmptyStr
from .repair import RepairState
from .run import RunState

type Confidence = Annotated[float, Ge(0.0), Le(1.0)]
type FindingCount = Annotated[int, Ge(0)]


class RunRecordFields:
    """Group the flat fields of one recorded verdict by what produced each of them."""

    class Verdict(FrozenModel):
        """Retain which rule concluded what about which subject.

        The subject is what a receiving system stores the verdict against, and `identity` is the
        thing inside it the verdict is actually about, which for ordinary source is the file and
        symbol a finding named. Leaving `identity` empty means the subject is itself the identity,
        which is what a warehouse asset already is.
        """

        rule: NonEmptyStr
        subject: NonEmptyStr
        identity: str = ""
        path: str = ""
        summary: str = ""
        state: RunState = RunState.SUCCESS

        @property
        def anchor(self) -> str:
            """Return the exact thing this verdict is about, which its record is keyed by."""
            return self.identity or self.subject

    class Evidence(Verdict):
        """Retain the measurement and reported reasons behind that verdict."""

        measurement: str = ""
        finding_count: FindingCount = 0
        reasons: list[str] = []
        repair: RepairState = RepairState.NONE

    class Estimate(Evidence):
        """Retain what a contextual backend said, which only an estimated rule carries."""

        reasoning: str = ""
        confidence: Confidence | None = None
