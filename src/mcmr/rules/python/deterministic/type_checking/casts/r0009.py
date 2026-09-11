import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import CallFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import CallRelation, Table

_CAST_NAMES = ["typing.cast", "typing_extensions.cast"]


def _arguments(subject: Table[CallFact]) -> pl.LazyFrame:
    """Read the target type and the asserted expression out of each call's argument rows."""
    return (
        subject.lazy(CallRelation.EXPRESSIONS)
        .filter((pl.col("root_relation") == "argument") & (pl.col("depth") == 0))
        .group_by("call_id", maintain_order=True)
        .agg(
            pl.col("text").filter(pl.col("root_ordinal") == 0).first().alias("cast_target"),
            pl.col("text").filter(pl.col("root_ordinal") == 1).first().alias("producer_text"),
        )
    )


@rule("PY-TYPE0009", policy=Numeric(maximum=0))
def cast_calls(subject: Table[CallFact]) -> CountQuery:
    """Count every call resolved to `typing.cast`.

    Definition
    ----------
    Count each call whose callee resolves to `typing.cast` or `typing_extensions.cast`, whatever
    name the import bound it to, and return that count for the file. A cast asserts a type the
    checker could not prove and performs no runtime work, so every one is a contract the code
    declined to state. That contract is an annotation on the receiving name when the producer
    is untyped, a `Protocol` or an overload when the producer is typed too widely, and a
    validating boundary when the value came from outside the process.

    Evidence
    --------
    Each finding names the target type and the expression the cast asserts about, at the exact
    location of the call. The value is the number of such calls in the file, and the default
    ceiling of zero refuses them all. `PY-TYPE0005` separately groups the ones that repeat.

    Exceptions
    ----------
    A project that has to keep one cast at an untyped third-party boundary raises the ceiling or
    excludes that module through the rule's policy rather than the code. A name `cast` that
    resolves to something other than the typing modules is not counted.

    Examples
    --------
    Bad
    ~~~
    `stream = cast("Stream", module.Stream())` asserts what an annotation states as well.

    Good
    ~~~~
    `stream: Stream = module.Stream()` is checked at the assignment and reads without the call,
    and `Record.model_validate(raw)` validates a value that came from outside.

    References
    ----------
    Cites "Python typing specification", Type checker directives, `cast()`
    https://typing.python.org/en/latest/spec/directives.html#cast
    Cites "Mypy documentation", `redundant-cast`
    https://mypy.readthedocs.io/en/stable/error_code_list2.html#check-that-cast-is-not-redundant-redundant-cast
    """
    facts = subject.lazy(CallRelation.FACTS)
    evidence = (
        subject.lazy(CallRelation.EVIDENCE)
        .group_by("fact_id", maintain_order=True)
        .agg(pl.col("signal").sort_by("ordinal").alias("evidence"))
    )
    casts = (
        subject.lazy(CallRelation.CALLS)
        .filter(pl.col("qualified_name").is_in(_CAST_NAMES))
        .join(_arguments(subject), on="call_id", how="left")
        .with_columns(pl.col("cast_target").fill_null(""), pl.col("producer_text").fill_null(""))
    )
    counts = casts.group_by("fact_id", maintain_order=True).agg(
        pl.len().cast(pl.UInt64).alias("value")
    )
    frame = facts.join(counts, on="fact_id", how="left").with_columns(pl.col("value").fill_null(0))
    finding_rows = (
        casts.select(
            "fact_id",
            "ordinal",
            "cast_target",
            "producer_text",
            pl.col("node_path").alias("path"),
            pl.col("node_start_line").alias("start_line"),
            pl.col("node_start_column").alias("start_column"),
            pl.col("node_end_line").alias("end_line"),
            pl.col("node_end_column").alias("end_column"),
        )
        .join(evidence, on="fact_id", how="left")
        .with_columns(pl.col("evidence").fill_null(pl.lit([], dtype=pl.List(pl.String))))
    )
    return RuleQuery.integer(
        frame,
        pl.col("value"),
        findings=FindingQuery.build(
            finding_rows,
            pl.concat_str(
                pl.lit("`cast` to `"),
                pl.col("cast_target"),
                pl.lit("` asserts about `"),
                pl.col("producer_text"),
                pl.lit("` in place of a checked annotation"),
            ),
            (("casts", pl.lit(1), Unit.COUNT),),
            finding_order=pl.col("ordinal"),
            evidence=pl.col("evidence"),
        ),
    )
