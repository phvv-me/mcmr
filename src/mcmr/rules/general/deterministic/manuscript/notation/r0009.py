import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0009", policy=Numeric(maximum=0))
def symbol_introduced_under_two_meanings(
    subject: Table[ManuscriptNotationFact],
    *,
    minimum_sections: PositiveInt = 2,
) -> CountQuery:
    """Count symbols the manuscript introduces twice without saying it did.

    Definition
    ----------
    One symbol carrying two meanings is the defect a cold reader loses the most time to, because
    nothing tells them the meaning changed. Collect the places a manuscript introduces each symbol,
    which is where the symbol stands alone on the left of a display equality or where a definition
    cue precedes it in prose. Report a symbol introduced in at least `minimum_sections` different
    sections whose own notation index row separates no senses.

    An index row that says `elsewhere`, `instead`, or otherwise names a second sense has declared
    the reuse, and a declared reuse is a convention rather than a trap.

    Evidence
    --------
    Each finding names the symbol, how many sections introduce it, and where the first two of
    those introductions are. The value is the number of undeclared reuses.

    Exceptions
    ----------
    A symbol reintroduced in a later section to restate the same meaning is reported, and the
    repair is usually to reference the first definition rather than to restate it. A definition cue
    detected in prose that was not one is the main source of noise here, which is why the rule
    requires two different sections rather than two sites. A manuscript with no notation index has
    declared nothing, so every twice-introduced symbol is reported.

    Examples
    --------
    Bad
    ~~~
    `$K$` introduced as a reduction depth in chapter one and as a kernel matrix in chapter two,
    with one index row, returns `1`.

    Good
    ~~~~
    The same `$K$` whose index row reads `Also, in \\Cref{def:gemm}, the reduction depth` returns
    `0`, and so does a symbol introduced once.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, notation
    Cites "Mathematical Writing", Knuth, Larrabee and Roberts, one meaning per symbol
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    sites = (
        relations.located("sites", "symbol")
        .group_by("fact_id", "symbol", maintain_order=True)
        .agg(
            pl.col("section_number").n_unique().cast(pl.UInt64).alias("section_count"),
            pl.col("reading_order").min().alias("reading_order"),
            pl.col("path").first(),
            pl.col("start_line").first(),
            pl.col("start_column").first(),
            pl.col("end_line").first(),
            pl.col("end_column").first(),
        )
    )
    declared = (
        relations.located("entries", "symbol", "sense_count")
        .group_by("fact_id", "symbol", maintain_order=True)
        .agg(pl.col("sense_count").max().alias("declared_senses"))
    )
    collided = (
        sites.join(declared, on=["fact_id", "symbol"], how="left")
        .with_columns(pl.col("declared_senses").fill_null(1))
        .filter((pl.col("section_count") >= minimum_sections) & (pl.col("declared_senses") < 2))
    )
    return RuleQuery.integer(
        relations.counted(collided),
        pl.col("value"),
        findings=FindingQuery.build(
            collided,
            pl.concat_str(
                pl.lit("`"),
                pl.col("symbol"),
                pl.lit("` is introduced in "),
                pl.col("section_count").cast(pl.String),
                pl.lit(" different sections and the index separates no senses"),
            ),
            (("undeclared symbol reuses", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
