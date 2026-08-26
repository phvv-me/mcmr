import polars as pl
from pydantic import PositiveFloat, PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptEvidenceFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0013", policy=Numeric(maximum=0))
def prose_number_that_nearly_matches_its_table(
    subject: Table[ManuscriptEvidenceFact],
    *,
    tolerance: PositiveFloat = 0.02,
    minimum_digits: PositiveInt = 4,
) -> CountQuery:
    """Count reported numbers that almost, but not exactly, match the table they cite.

    Definition
    ----------
    A prose number that appears nowhere near a table says nothing, because the evidence for it can
    live anywhere. A prose number that lands within `tolerance` of a cell in a table the same
    section references and is not equal to it says a great deal, because it is the same quantity
    printed twice with two different values. Report a number of at least `minimum_digits` digits
    carrying a decimal point whose closest cell in a referenced table differs from it by more than
    nothing and by no more than `tolerance` in relative terms.

    That is the shape of every disagreement worth catching. A prose value copied before a rerun, a
    share computed from means rather than as a mean of ratios, and a figure rounded one way in the
    text and another in the table all land inside the band and none of them land on it.

    Evidence
    --------
    Each finding names the number the prose states, the closest cell in a referenced table, and
    the relative difference between them. The value is the number of near misses.

    Exceptions
    ----------
    A prose number equal to its cell is never reported, and neither is one that no cell comes
    close to, since that is a different quantity rather than a disagreement. A section that
    references no table reports nothing. Two genuinely different measurements that happen to lie
    within a couple of percent of each other are the false positive this rule accepts in exchange
    for finding the ones that are not, and stating both in the same table is the repair.

    Examples
    --------
    Bad
    ~~~
    Prose reading `the share is 0.042399` in a section referencing a table whose cell reads
    `0.042668` returns `1`.

    Good
    ~~~~
    Prose quoting `0.042668` exactly returns `0`, and so does prose stating `19.8151` where the
    nearest cell is `2.9024`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, presenting results
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    stated = pl.col("literal").str.replace_all(",", "").cast(pl.Float64, strict=False)
    numbers = (
        relations.located("numbers", "literal", "in_cells", "float_label")
        .filter(
            pl.col("literal").str.contains(".", literal=True)
            & (pl.col("literal").str.count_matches(r"[0-9]") >= minimum_digits)
        )
        .with_columns(stated.alias("stated"))
        .filter(pl.col("stated").is_not_null() & (pl.col("stated") != 0.0))
    )
    cells = numbers.filter(
        pl.col("in_cells") & (pl.col("float_label").str.len_chars() > 0)
    ).select("fact_id", pl.col("float_label").alias("cited_label"), pl.col("stated").alias("held"))
    cited = (
        relations.located("references", "target")
        .select("fact_id", "section_number", pl.col("target").alias("cited_label"))
        .unique()
    )
    reachable = cited.join(cells, on=["fact_id", "cited_label"], how="inner").select(
        "fact_id", "section_number", "held"
    )
    near = (
        numbers.filter(~pl.col("in_cells"))
        .join(reachable, on=["fact_id", "section_number"], how="inner")
        .with_columns(
            ((pl.col("stated") - pl.col("held")).abs() / pl.col("stated").abs()).alias("gap")
        )
        .filter((pl.col("gap") > 0.0) & (pl.col("gap") <= tolerance))
        .sort("gap")
        .unique(subset=["fact_id", "record_id"], keep="first")
    )
    return RuleQuery.integer(
        relations.counted(near),
        pl.col("value"),
        findings=FindingQuery.build(
            near,
            pl.concat_str(
                pl.lit("prose states `"),
                pl.col("literal"),
                pl.lit("` where the nearest referenced cell reads `"),
                pl.col("held").round_sig_figs(6).cast(pl.String),
                pl.lit("`"),
            ),
            (("near misses against a cited table", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
