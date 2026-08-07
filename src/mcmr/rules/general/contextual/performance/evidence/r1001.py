from enum import StrEnum, auto

from ...... import Category, rule
from ......execution import ClassificationBackend
from ......execution.queries import ModelQuery
from ......facts import PerformanceDecisionFact
from ......table import Table


class ProfilingEvidence(StrEnum):
    SUFFICIENT = auto()
    STALE = auto()
    INCOMPLETE = auto()
    ABSENT = auto()
    NOT_NEEDED = auto()
    UNCERTAIN = auto()


@rule(
    "ALL-PERF1001",
    policy=Category.outcomes(good={"not_needed", "sufficient"}, neutral={"uncertain"}),
)
def profiling_evidence(
    subject: Table[PerformanceDecisionFact],
    backend: ClassificationBackend,
) -> ModelQuery[ProfilingEvidence]:
    """Judge whether a performance decision has adequate profiling evidence.

    Definition
    ----------
    Check workload, environment, baseline, profiler, measured resource, bottleneck, and
    recency before accepting performance evidence.

    Evidence
    --------
    Findings cite profiles, commands, hardware, workloads, baselines, and timestamps.

    Exceptions
    ----------
    Removing obviously dead work can be justified without a full profile when behavior is proven.

    Examples
    --------
    A saved profile over the production workload is `sufficient`. A microbenchmark from an old
    implementation is `stale` for a current system claim.

    References
    ----------
    Cites "Systems Performance"
    Cites "The Python Standard Library", profiling
    """
    return backend.classification(
        subject,
        category=ProfilingEvidence,
        instructions=profiling_evidence.instructions,
    )
