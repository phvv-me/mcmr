import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0007", policy=Numeric(maximum=0))
def symbol_missing_from_the_notation_index(
    subject: Table[ManuscriptNotationFact],
    *,
    minimum_sections: PositiveInt = 2,
    minimum_uses: PositiveInt = 3,
) -> CountQuery:
    """Count symbols the manuscript uses widely and its own index never lists.

    Definition
    ----------
    A manuscript that keeps a notation index is promising a reader one place to look every symbol
    up, and the promise is only worth anything if the index is complete. Report a symbol appearing
    in at least `minimum_sections` sections and used at least `minimum_uses` times that no index
    row names, matched on the exact spelling the body writes.

    A manuscript with no index at all reports nothing, because there is no promise to break.

    Evidence
    --------
    Each finding names the symbol, how often it is used, and how many sections it crosses. The
    value is the number of widely used symbols the index omits.

    Exceptions
    ----------
    A symbol confined to one section is local and reports nothing, however often it appears there,
    which is the convention every index states for itself. Matching is on spelling, so an index
    listing one subscripted form of a letter does not cover another form of the same letter, and
    that is deliberate, since a reader looking up the second finds the first and reads the wrong
    meaning. A symbol introduced only inside a display the index cites is still reported when the
    index does not name the symbol itself.

    Examples
    --------
    Bad
    ~~~
    `$w_e$` used in three sections while the index lists only `$w$` returns `1`.

    Good
    ~~~~
    A symbol the index lists returns `0`, and so does every symbol in a manuscript that keeps no
    index.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, notation tables
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    entries = relations.located("entries", "symbol").select(
        "fact_id", pl.col("symbol").alias("indexed")
    )
    symbols = relations.located("symbols", "name", "use_count", "section_count").filter(
        (pl.col("section_count") >= minimum_sections) & (pl.col("use_count") >= minimum_uses)
    )
    missing = symbols.join(
        entries.unique(),
        left_on=["fact_id", "name"],
        right_on=["fact_id", "indexed"],
        how="anti",
    ).join(entries.select("fact_id").unique(), on="fact_id", how="semi")
    return RuleQuery.integer(
        relations.counted(missing),
        pl.col("value"),
        findings=FindingQuery.build(
            missing,
            pl.concat_str(
                pl.lit("`"),
                pl.col("name"),
                pl.lit("` crosses "),
                pl.col("section_count").cast(pl.String),
                pl.lit(" sections and the notation index never lists it"),
            ),
            (("symbols the index omits", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
