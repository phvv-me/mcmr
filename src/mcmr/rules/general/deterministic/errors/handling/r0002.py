import re

import polars as pl

from ...... import rule
from ......domain.contracts import Unit
from ......facts import SyntaxFact
from ......query import FindingQuery, RuleQuery
from ......table import SyntaxRelation, Table
from ......table.relations import SyntaxTable

# The words a raise states, which is all the evidence there is that it carried the original along.
_WORD = r"[A-Za-z_][A-Za-z0-9_]*"


def _guarded_lines(relations: SyntaxTable[SyntaxFact], nodes: pl.LazyFrame) -> pl.LazyFrame:
    """Return one row per source line of every guard, beside its indentation and located span."""
    guards = relations.with_text(nodes.filter(pl.col("kind") == "guard")).select(
        "fact_id",
        pl.col("ordinal").alias("guard_ordinal"),
        pl.col("subtree_end").alias("guard_end"),
        pl.col("start_line").alias("guard_start_line"),
        pl.col("path").alias("finding_path"),
        pl.col("start_line").alias("finding_start_line"),
        pl.col("start_column").alias("finding_start_column"),
        pl.col("end_line").alias("finding_end_line"),
        pl.col("end_column").alias("finding_end_column"),
        pl.col("text").str.split("\n").alias("lines"),
    )
    return (
        guards.with_columns(pl.int_ranges(0, pl.col("lines").list.len()).alias("offset"))
        .explode("lines", "offset", empty_as_null=True)
        .with_columns(
            (
                pl.col("lines").str.len_chars()
                - pl.col("lines").str.strip_chars_start().str.len_chars()
            ).alias("indent"),
            pl.col("lines").str.strip_chars().alias("stripped"),
        )
    )


def _handler_clauses(lines: pl.LazyFrame, handlers: tuple[str, ...]) -> pl.LazyFrame:
    """Return every handler clause a guard opens, beside the name it binds the failure to."""
    opening = r"^[}\t ]*(?:" + "|".join(map(re.escape, handlers)) + r")\b"
    bound_by_name = pl.col("header").str.split(" as ").list.last().str.strip_chars(" :{)")
    bound_by_position = (
        pl.col("header")
        .str.extract(r"\((.+)\)", 1)
        .fill_null("")
        .str.extract_all(_WORD)
        .list.last()
        .fill_null("")
    )
    return (
        lines.filter(pl.col("lines").str.contains(opening))
        .select(
            "fact_id",
            "guard_ordinal",
            "guard_end",
            "guard_start_line",
            "finding_path",
            "finding_start_line",
            "finding_start_column",
            "finding_end_line",
            "finding_end_column",
            pl.col("offset").alias("handler_offset"),
            pl.col("indent").alias("margin"),
            pl.col("lines").alias("header"),
        )
        .with_row_index("handler_id")
        .with_columns(
            pl.when(pl.col("header").str.contains(" as ", literal=True))
            .then(bound_by_name)
            .otherwise(
                pl.when(~pl.col("header").str.strip_chars_end().str.ends_with(":"))
                .then(bound_by_position)
                .otherwise(pl.lit(""))
            )
            .alias("caught")
        )
    )


def _clause_boundaries(clauses: pl.LazyFrame, *, lines: pl.LazyFrame) -> pl.LazyFrame:
    """Return the offset of the first line each handler clause no longer holds."""
    return (
        clauses.join(lines, on=["fact_id", "guard_ordinal"], how="inner")
        .filter(
            (pl.col("offset") > pl.col("handler_offset"))
            & ~((pl.col("indent") > pl.col("margin")) | pl.col("stripped").is_in(["{", ""]))
        )
        .group_by("handler_id", maintain_order=True)
        .agg(pl.col("offset").min().alias("boundary"))
    )


def _raises_inside_clauses(
    relations: SyntaxTable[SyntaxFact],
    nodes: pl.LazyFrame,
    *,
    clauses: pl.LazyFrame,
    boundaries: pl.LazyFrame,
    raises: tuple[str, ...],
) -> pl.LazyFrame:
    """Return every raise a handler clause holds, carrying the clause that would answer it."""
    raised = relations.with_text(nodes.filter(pl.col("kind").is_in(list(raises)))).select(
        "fact_id", "ordinal", "start_line", "text"
    )
    return (
        clauses.join(boundaries, on="handler_id", how="left")
        .join(raised, on="fact_id", how="inner")
        .filter(
            (pl.col("ordinal") > pl.col("guard_ordinal"))
            & (pl.col("ordinal") < pl.col("guard_end"))
            & (pl.col("start_line") >= pl.col("guard_start_line") + pl.col("handler_offset"))
            & (
                pl.col("boundary").is_null()
                | (pl.col("start_line") < pl.col("guard_start_line") + pl.col("boundary"))
            )
        )
    )


def _without_cause(raised: pl.LazyFrame, causes: tuple[str, ...]) -> pl.LazyFrame:
    """Keep the raises whose own words name neither a cause marker nor the failure caught."""
    return raised.with_columns(pl.col("text").str.extract_all(_WORD).alias("stated")).filter(
        (pl.col("stated").list.len() > 1)
        & ~pl.col("stated").list.eval(pl.element().is_in(list(causes))).list.any()
        & ~pl.col("stated").list.contains(pl.col("caught"))
    )


@rule("ALL-ERRO0002")
def raise_without_cause(
    subject: Table[SyntaxFact],
    *,
    handlers: tuple[str, ...] = ("except", "catch", "rescue"),
    raises: tuple[str, ...] = ("raise", "throw"),
    causes: tuple[str, ...] = ("from", "cause"),
) -> RuleQuery[int]:
    """Count errors raised inside a handler that arrive without the failure they replace.

    Definition
    ----------
    Read every guard one declaration states and report a raise written inside a handler clause
    whose own text names neither the failure that clause caught nor a marker that carries a cause.
    Translating a low level failure into one the caller understands is good practice, and it stays
    good practice only while the new error carries the old one, because the stack that names what
    actually broke lives on the failure being replaced. Python spells the carry as `from error`,
    JavaScript as the `cause` option, Java by handing the caught error to the constructor, and Go
    by wrapping with `%w`. A raise a formatter wrapped over several lines is read through to the
    parenthesis that closes it, so the cause still counts wherever it was written.

    Losing that stack costs a whole debugging session. The report says the profile could not be
    read and never says the disk was full, so whoever is holding the incident has to reproduce
    from scratch what the program already knew and then threw away.

    Evidence
    --------
    Each finding names the declaration, the handler clause, and the raise that arrives with no
    cause. The value is the number of raises that drop what they replace.

    Exceptions
    ----------
    A raise that states a cause marker or names the caught failure itself is carrying the original
    and is left alone. Deliberately breaking the chain with `raise ... from None` says so in the
    source, and it reads as carried for exactly that reason. A bare re-raise names no new error at
    all and hands the original straight on, so it is never judged, and neither is a raise outside a
    handler because it replaces nothing. A handler that binds no name is judged on the markers
    alone, since there is no name a raise there could carry. Only a callable is judged, because a
    type reaches every handler it owns through the callable holding it and would otherwise report
    the same raise twice. `handlers` names the words a language opens a handler clause with,
    `raises` the words it raises with, and `causes` the markers that carry one, so a language
    spelling any of them differently is configured rather than reimplemented.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       try:
           profile = read(path)
       except OSError as error:
           raise ConfigurationError("the profile is unreadable")

    Good
    ~~~~
    .. code-block:: python

       try:
           profile = read(path)
       except OSError as error:
           raise ConfigurationError("the profile is unreadable") from error

    References
    ----------
    Generalizes Ruff B904 raise-without-from-inside-except
    https://docs.astral.sh/ruff/rules/raise-without-from-inside-except/
    Cites "PEP 3134, Exception Chaining and Embedded Tracebacks"
    https://peps.python.org/pep-3134/
    Cites "MDN Web Docs", the Error cause option
    https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/cause
    Cites "The Go documentation", error wrapping with the `%w` verb
    https://go.dev/blog/go1.13-errors
    Cites "Effective Java", item 73, throw exceptions appropriate to the abstraction
    """
    relations = SyntaxTable(table=subject)
    facts = subject.lazy(SyntaxRelation.FACTS)
    nodes = relations.nodes
    lines = _guarded_lines(relations, nodes)
    clauses = _handler_clauses(lines, handlers)
    held = _raises_inside_clauses(
        relations,
        nodes,
        clauses=clauses,
        boundaries=_clause_boundaries(clauses, lines=lines),
        raises=raises,
    )
    reported = (
        _without_cause(held, causes)
        .group_by("fact_id", "guard_ordinal", maintain_order=True)
        .agg(
            pl.len().cast(pl.UInt64).alias("amount"),
            pl.col("finding_path").first().alias("path"),
            pl.col("finding_start_line").first().alias("start_line"),
            pl.col("finding_start_column").first().alias("start_column"),
            pl.col("finding_end_line").first().alias("end_line"),
            pl.col("finding_end_column").first().alias("end_column"),
        )
    )
    counts = reported.group_by("fact_id", maintain_order=True).agg(
        pl.col("amount").sum().cast(pl.UInt64).alias("value")
    )
    joined = facts.join(counts, on="fact_id", how="left").with_columns(
        pl.when(pl.col("kind") == "callable")
        .then(pl.col("value").fill_null(0))
        .otherwise(0)
        .alias("value")
    )
    callable_reported = reported.join(
        facts.filter(pl.col("kind") == "callable").select("fact_id"),
        on="fact_id",
        how="inner",
    )
    location = (
        pl.when(pl.col("end_line") > pl.col("start_line"))
        .then(
            pl.concat_str(
                pl.col("path"),
                pl.lit(":"),
                pl.col("start_line"),
                pl.lit("-"),
                pl.col("end_line"),
            )
        )
        .otherwise(pl.concat_str(pl.col("path"), pl.lit(":"), pl.col("start_line")))
    )
    findings = FindingQuery.build(
        callable_reported,
        pl.concat_str(
            pl.lit("guard at `"),
            location,
            pl.lit("` raises "),
            pl.col("amount"),
            pl.lit(" replacement errors without their causes"),
        ),
        (("raise without cause", pl.col("amount"), Unit.COUNT),),
        finding_order=pl.col("guard_ordinal"),
    )
    return RuleQuery.integer(joined, pl.col("value"), findings=findings)
