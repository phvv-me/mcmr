from enum import StrEnum, auto

import polars as pl

from ..... import Category, rule
from .....execution import ClassificationBackend
from .....execution.queries import ModelQuery
from .....facts import CallFact
from .....table import Table


class DiagnosticContext(StrEnum):
    ACTIONABLE = auto()
    SPARSE = auto()
    NOISY = auto()
    UNSAFE = auto()
    UNCERTAIN = auto()


@rule(
    "ALL-OBSE1001",
    policy=Category.outcomes(good={"actionable"}, neutral={"uncertain"}),
)
def diagnostic_context(
    subject: Table[CallFact],
    backend: ClassificationBackend,
) -> ModelQuery[DiagnosticContext]:
    """Judge whether telemetry carries useful and safe diagnostic context.

    Definition
    ----------
    Compare operational questions, event identity, outcome, correlation, dimensions, errors,
    cardinality, privacy, volume, and downstream search or aggregation needs. A call reaches this
    pass when it names a log level, a metric emitter, or a tracing operation, which is what a
    signal is spelled as in every language this reads.

    Evidence
    --------
    Findings cite signal schemas, examples, operational questions, costs, and sensitive fields.

    Exceptions
    ----------
    Hot paths may emit compact signals when correlation links to richer context elsewhere. A bare
    `span` is not a signal, because every parser, AST, and macro library answers `span` with the
    source range of a node, so a tracing span is recognized by the operation that starts or
    annotates one rather than by the word alone.

    Examples
    --------
    A failed request signal with operation, outcome, trace, and safe account class is `actionable`.
    Repeating full payloads on every step is `noisy` and unsafe.

    References
    ----------
    Cites "OpenTelemetry Semantic Conventions"
    Cites "Observability Engineering", context-rich debugging
    Cites "Site Reliability Engineering", monitoring distributed systems
    """
    telemetry = (
        r"(?i)(?:^|\.)(?:debug|info|warn|warning|error|exception|critical|log|metric|"
        r"counter|histogram|gauge|trace|emit|observe|increment|add_event|record_exception|"
        r"set_attribute|set_attributes|start_span|start_active_span|start_as_current_span)$"
    )
    return backend.classification(
        subject,
        category=DiagnosticContext,
        instructions=diagnostic_context.instructions,
    ).where(pl.col("qualified_name").str.contains(telemetry) & ~pl.col("is_test"))
