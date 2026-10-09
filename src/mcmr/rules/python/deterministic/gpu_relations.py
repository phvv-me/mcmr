from typing import TYPE_CHECKING

import polars as pl

from ....domain.contracts import Unit
from ....query import CountQuery, FindingQuery, RuleQuery
from ....table import CallRelation, FunctionRelation, SyntaxRelation, Table

if TYPE_CHECKING:
    from ....facts import CallFact, FunctionFact, SyntaxFact


def compiled_functions(subject: Table[FunctionFact], *roles: str) -> pl.LazyFrame:
    """Return every function Numba compiles in one of `roles`, at any scope.

    roles: `kernel` for a launched kernel, `device` for a device function, either one written
        with Numba's `cuda.jit` or patos.cuda's `kernel`, `device`, and `ptx`, a record's methods
        included.
    """
    return (
        subject.lazy(FunctionRelation.FUNCTIONS)
        .filter(pl.col("device_role").is_in(roles))
        .select(
            "entity_id",
            "name",
            pl.col("definition_path").alias("path"),
            "definition_start_line",
            "definition_start_column",
            "definition_end_line",
        )
    )


def compiled_declarations(
    subject: Table[SyntaxFact], functions: Table[FunctionFact], *roles: str
) -> pl.LazyFrame:
    """Return the declaration of every function Numba compiles in one of `roles`.

    A declaration and its function start at the same decorator, which is what joins a record's
    method to its own `Record.method` declaration as well as a module function to its name.
    """
    return (
        subject.lazy(SyntaxRelation.FACTS)
        .join(
            compiled_functions(functions, *roles),
            left_on=["path", "start_line", "start_column"],
            right_on=["path", "definition_start_line", "definition_start_column"],
            how="inner",
        )
        .select("fact_id", "qualname", "entity_id")
    )


def record_constants(subject: Table[SyntaxFact], functions: Table[FunctionFact]) -> pl.LazyFrame:
    """Return each compiled record method with every field its record declares `Constant[...]`.

    patos.cuda compiles such a field into the record's device type, so a method reads it as a
    literal: one row per method declaration, its function, and one such field.
    """
    nodes = subject.lazy(SyntaxRelation.NODES)
    first_children = subject.lazy(SyntaxRelation.CHILDREN).filter(pl.col("child_order") == 0)
    records = (
        subject.lazy(SyntaxRelation.FACTS)
        .filter(pl.col("kind") == "type")
        .select("fact_id", "path", pl.col("qualname").alias("record"))
    )
    constants = (
        nodes.filter((pl.col("kind") == "binding") & (pl.col("depth") == 2))
        .select(
            "fact_id", pl.col("ordinal").alias("parent_ordinal"), pl.col("name").alias("field")
        )
        .join(first_children, on=["fact_id", "parent_ordinal"], how="inner")
        .join(
            nodes.filter(pl.col("kind") == "index").select(
                "fact_id", pl.col("ordinal").alias("child_ordinal")
            ),
            on=["fact_id", "child_ordinal"],
            how="inner",
        )
        .select("fact_id", "field", pl.col("child_ordinal").alias("parent_ordinal"))
        .join(first_children, on=["fact_id", "parent_ordinal"], how="inner")
        .join(
            nodes.filter(pl.col("name") == "Constant").select(
                "fact_id", pl.col("ordinal").alias("child_ordinal")
            ),
            on=["fact_id", "child_ordinal"],
            how="inner",
        )
        .join(records, on="fact_id", how="inner")
        .select("path", "record", "field")
    )
    return (
        compiled_declarations(subject, functions, "kernel", "device")
        .join(
            compiled_functions(functions, "kernel", "device").select("entity_id", "path"),
            on="entity_id",
            how="inner",
        )
        .filter(pl.col("qualname").str.contains(".", literal=True))
        .with_columns(pl.col("qualname").str.replace(r"\.[^.]+$", "").alias("record"))
        .join(constants, on=["path", "record"], how="inner")
        .select("fact_id", "entity_id", "field")
    )


def call_rows(subject: Table[CallFact]) -> pl.LazyFrame:
    """Return calls belonging to the selected fact rows."""
    facts = subject.lazy(CallRelation.FACTS).select("fact_id")
    return subject.lazy(CallRelation.CALLS).join(facts, on="fact_id", how="inner")


def counted_calls(
    subject: Table[CallFact],
    selected: pl.LazyFrame,
    message: pl.Expr,
    measurement: str,
) -> CountQuery:
    """Count selected calls per source file and retain each exact call as a finding."""
    facts = subject.lazy(CallRelation.FACTS)
    counts = selected.group_by("fact_id", maintain_order=True).agg(
        pl.len().cast(pl.UInt64).alias("value")
    )
    values = facts.join(counts, on="fact_id", how="left").with_columns(
        pl.col("value").fill_null(0)
    )
    evidence = (
        subject.lazy(CallRelation.EVIDENCE)
        .group_by("fact_id", maintain_order=True)
        .agg(pl.col("signal").sort_by("ordinal").alias("evidence"))
    )
    findings = selected.join(evidence, on="fact_id", how="left").with_columns(
        pl.col("node_path").alias("path"),
        pl.col("node_start_line").alias("start_line"),
        pl.col("node_start_column").alias("start_column"),
        pl.col("node_end_line").alias("end_line"),
        pl.col("node_end_column").alias("end_column"),
        pl.col("evidence").fill_null(pl.lit([], dtype=pl.List(pl.String))),
    )
    return RuleQuery.integer(
        values,
        pl.col("value"),
        findings=FindingQuery.build(
            findings,
            message,
            ((measurement, pl.lit(1), Unit.COUNT),),
            finding_order=pl.col("ordinal"),
            evidence=pl.col("evidence"),
        ),
    )


def counted_syntax(
    subject: Table[SyntaxFact],
    selected: pl.LazyFrame,
    message: pl.Expr,
    measurement: str,
) -> CountQuery:
    """Count selected syntax nodes per declaration and retain their exact spans."""
    facts = subject.lazy(SyntaxRelation.FACTS)
    counts = selected.group_by("fact_id", maintain_order=True).agg(
        pl.len().cast(pl.UInt64).alias("value")
    )
    values = facts.join(counts, on="fact_id", how="left").with_columns(
        pl.col("value").fill_null(0)
    )
    return RuleQuery.integer(
        values,
        pl.col("value"),
        findings=FindingQuery.build(
            selected,
            message,
            ((measurement, pl.lit(1), Unit.COUNT),),
            finding_order=pl.col("ordinal"),
        ),
    )
