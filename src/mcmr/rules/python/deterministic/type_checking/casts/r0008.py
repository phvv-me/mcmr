import polars as pl

from ...... import rule
from ......domain.contracts import (
    FixSafety,
    Unit,
)
from ......facts import CallFact
from ......query import CountQuery, FindingQuery, FixQuery, RuleQuery
from ......table import CallRelation, Table

# What the single positional operand of a conversion is called once it is read out of the call.
_OPERAND = {
    "text": "operand_text",
    "resolved_type": "operand_type",
    "node_id": "operand_id",
    "node_path": "operand_path",
    "node_start_line": "operand_start_line",
    "node_start_column": "operand_start_column",
    "node_end_line": "operand_end_line",
    "node_end_column": "operand_end_column",
    "node_kind": "operand_kind",
    "node_text": "operand_node_text",
}


def _operands(subject: Table[CallFact]) -> pl.LazyFrame:
    """Read the one positional operand each call was given out of its expression rows."""
    return (
        subject.lazy(CallRelation.EXPRESSIONS)
        .filter((pl.col("root_relation") == "argument") & (pl.col("depth") == 0))
        .group_by("call_id", maintain_order=True)
        .agg(
            pl.len().cast(pl.UInt64).alias("argument_count"),
            *(
                pl.col(column).filter(pl.col("root_ordinal") == 0).first().alias(name)
                for column, name in _OPERAND.items()
            ),
        )
    )


def _proven_conversions(subject: Table[CallFact], facts: pl.LazyFrame) -> pl.LazyFrame:
    """Return every unshadowed one-argument `bool` call whose operand is already Boolean."""
    keyword_calls = subject.lazy(CallRelation.KEYWORDS).select("call_id").unique()
    return (
        subject.lazy(CallRelation.CALLS)
        .join(facts.select("fact_id"), on="fact_id", how="inner")
        .join(_operands(subject), on="call_id", how="inner")
        .join(keyword_calls, on="call_id", how="anti")
        .filter(
            (pl.col("qualified_name") == "builtins.bool")
            & ~pl.col("is_shadowed")
            & (pl.col("argument_count") == 1)
            & (pl.col("operand_type") == "bool")
        )
    )


def _span(repairable: pl.LazyFrame, *, role: str, prefix: str, text: str) -> pl.LazyFrame:
    """Name one span the repair points at, read out of the columns `prefix` names."""
    return repairable.select(
        "fact_id",
        pl.col("ordinal").alias("rewrite_order"),
        pl.lit(role).alias("role"),
        pl.lit(0, dtype=pl.UInt64).alias("ordinal"),
        pl.col(f"{prefix}_id").alias("id"),
        pl.col(f"{prefix}_path").alias("path"),
        pl.col(f"{prefix}_start_line").alias("start_line"),
        pl.col(f"{prefix}_start_column").alias("start_column"),
        pl.col(f"{prefix}_end_line").alias("end_line"),
        pl.col(f"{prefix}_end_column").alias("end_column"),
        pl.col(f"{prefix}_kind").alias("kind"),
        pl.col(text).alias("text"),
    )


def _repair_frames(repairable: pl.LazyFrame) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    """Ask for the conversion to be unwrapped, naming the call to drop and the operand to keep."""
    rewrites = repairable.select(
        "fact_id",
        pl.col("ordinal").alias("rewrite_order"),
        pl.lit("unwrap").alias("kind"),
        pl.lit("").alias("source"),
        pl.lit("").alias("placement"),
        pl.lit("").alias("name"),
        pl.lit("").alias("symbol_id"),
        pl.lit("").alias("symbol_name"),
        pl.lit(False).alias("references_complete"),
    )
    nodes = pl.concat(
        [
            _span(repairable, role="target", prefix="node", text="node_text"),
            _span(repairable, role="keep", prefix="operand", text="operand_node_text"),
        ],
        how="vertical",
    )
    return rewrites, nodes


@rule("PY-TYPE0008", fix_safety=FixSafety.SAFE)
def redundant_boolean_conversion(subject: Table[CallFact]) -> CountQuery:
    """Count builtin `bool` calls whose operands are already proven Boolean.

    Definition
    ----------
    Resolve calls to the unshadowed builtin `bool` with exactly one positional argument. Report a
    call only when the operand is a Boolean literal, comparison, `not` expression, conditional with
    Boolean branches, Boolean operation whose every operand is proven Boolean, a name explicitly
    annotated as `bool`, or an unshadowed standard predicate with an exact Boolean return. Emit a
    safe source edit that removes the conversion while retaining parentheses and UTF-8 offsets.

    Evidence
    --------
    Each finding records the source range and the AST kind that proves the operand Boolean. The
    value is the number of redundant conversions.

    Exceptions
    ----------
    Truthiness is not Boolean identity. Do not report `bool(sequence)`, `bool(mapping)`,
    `bool(optional)`, an unannotated value, or an `and` or `or` expression containing any operand
    that may return a non-Boolean object. A shadowed `bool`, `all`, `any`, `callable`, `hasattr`,
    `isinstance`, or `issubclass` suppresses inference. Comments inside the call suppress the edit
    but retain the diagnostic.

    Examples
    --------
    Bad
    ~~~
    `bool(enabled)` is redundant when `enabled: bool`. So are `bool(value is None)` and
    `bool(all(checks))` when the builtin names are unshadowed.

    Good
    ~~~~
    `bool(items)` intentionally converts sequence truthiness. `bool(fragile)` remains necessary
    when `fragile` is a tuple of findings rather than an exact Boolean.

    References
    ----------
    Cites "The Python Language Reference", truth value testing
    https://docs.python.org/3/library/stdtypes.html#truth-value-testing
    Cites "The Python Standard Library", `bool`
    https://docs.python.org/3/library/functions.html#bool
    Cites "The Python Language Reference", Boolean operations
    https://docs.python.org/3/reference/expressions.html#boolean-operations
    """
    facts = subject.lazy(CallRelation.FACTS)
    evidence = (
        subject.lazy(CallRelation.EVIDENCE)
        .group_by("fact_id", maintain_order=True)
        .agg(pl.col("signal").sort_by("ordinal").alias("evidence"))
    )
    selected = _proven_conversions(subject, facts)
    counts = selected.group_by("fact_id", maintain_order=True).agg(
        pl.len().cast(pl.UInt64).alias("value")
    )
    frame = facts.join(counts, on="fact_id", how="left").with_columns(pl.col("value").fill_null(0))
    finding_rows = (
        selected.select(
            "fact_id",
            "ordinal",
            "operand_text",
            pl.col("node_path").alias("path"),
            pl.col("node_start_line").alias("start_line"),
            pl.col("node_start_column").alias("start_column"),
            pl.col("node_end_line").alias("end_line"),
            pl.col("node_end_column").alias("end_column"),
        )
        .join(evidence, on="fact_id", how="left")
        .with_columns(pl.col("evidence").fill_null(pl.lit([], dtype=pl.List(pl.String))))
    )
    rewrites, nodes = _repair_frames(selected.filter(pl.col("operand_id").is_not_null()))
    value = pl.col("value")
    return RuleQuery.integer(
        frame,
        value,
        findings=FindingQuery.build(
            finding_rows,
            pl.concat_str(
                pl.lit("`bool` redundantly converts the proven Boolean `"),
                pl.col("operand_text"),
                pl.lit("`"),
            ),
            (("redundant boolean conversion", pl.lit(1), Unit.COUNT),),
            finding_order=pl.col("ordinal"),
            evidence=pl.col("evidence"),
        ),
        fix=FixQuery.build(
            "Keep the Boolean operand and drop the conversion wrapped around it.",
            rewrites=rewrites,
            nodes=nodes,
        ),
    )
