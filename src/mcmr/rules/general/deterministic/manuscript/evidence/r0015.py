import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptEvidenceFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0015", policy=Numeric(maximum=0))
def measurement_resting_on_an_unpinned_citation(
    subject: Table[ManuscriptEvidenceFact],
    *,
    reach: PositiveInt = 4,
    minimum_digits: PositiveInt = 3,
) -> CountQuery:
    """Count numbers supported by a citation that names no page or section.

    Definition
    ----------
    A citation beside a number is a promise that the number came from that source. A reader
    checking it has to find it, and a work of two hundred pages with no locator is a promise
    nobody can keep. Report a citation carrying no bracketed locator that sits within `reach`
    reading positions of a prose number of at least `minimum_digits` digits.

    Evidence
    --------
    Each finding names the bibliography key, the number it sits beside, and where both are. The
    value is the number of unpinned citations standing next to a measurement.

    Exceptions
    ----------
    A citation beside a number that is the source's own identifier, such as a year, is reported
    and is the main source of noise, which is why the digit floor exists. A citation carrying a
    locator of any kind passes, whatever the locator says, since checking that a page number is
    the right page is not something a reader of the source can do either. A number a manuscript
    measured itself and cites nobody for reports nothing, which is the shape a self-contained
    result takes.

    Examples
    --------
    Bad
    ~~~
    `the reported speedup is 3.83 \\citep{someone2026}` returns `1`.

    Good
    ~~~~
    `the reported speedup is 3.83 \\citep[Table 2]{someone2026}` returns `0`, and so does a
    measured number with no citation near it.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, citing sources
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    numbers = (
        relations.located("numbers", "literal", "in_cells")
        .filter(
            ~pl.col("in_cells") & (pl.col("literal").str.count_matches(r"[0-9]") >= minimum_digits)
        )
        .select("fact_id", pl.col("reading_order").alias("number_order"), "literal")
    )
    citations = relations.located("citations", "key", "pin").filter(
        pl.col("pin").str.len_chars() == 0
    )
    unpinned = (
        citations.join(numbers, on="fact_id", how="inner")
        .filter((pl.col("number_order") - pl.col("reading_order")).abs() <= reach)
        .unique(subset=["fact_id", "record_id"], keep="first")
    )
    return RuleQuery.integer(
        relations.counted(unpinned),
        pl.col("value"),
        findings=FindingQuery.build(
            unpinned,
            pl.concat_str(
                pl.lit("`"),
                pl.col("key"),
                pl.lit("` supports `"),
                pl.col("literal"),
                pl.lit("` and names no page or section"),
            ),
            (("unpinned supporting citations", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
