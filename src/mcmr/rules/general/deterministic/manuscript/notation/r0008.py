import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0008", policy=Numeric(maximum=0))
def notation_entry_absent_from_the_body(
    subject: Table[ManuscriptNotationFact],
) -> CountQuery:
    """Count notation index rows naming a symbol the manuscript never uses.

    Definition
    ----------
    Completeness runs in both directions. A row indexing a symbol the body never sets is a leftover
    from an earlier draft, and a reader who looks it up learns something the document no longer
    says. Report an index row whose symbol appears in no math span anywhere in the body.

    Evidence
    --------
    Each finding names the symbol, the row it sits on, and what the row claims it means. The value
    is the number of index rows the body no longer supports.

    Exceptions
    ----------
    A row indexing a word rather than a symbol, such as a named convention, is reported here
    because the reader of the index cannot tell the two apart either, and the repair is to move
    the convention out of the symbol table. A symbol set only inside a verbatim block is invisible
    to the reader as mathematics and its row is reported.

    Examples
    --------
    Bad
    ~~~
    A row for `$\\kappa$` in a manuscript whose body renamed it returns `1`.

    Good
    ~~~~
    Every row naming a symbol the body still sets returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, notation tables
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    symbols = relations.located("symbols", "name").select("fact_id", pl.col("name").alias("used"))
    stale = relations.located("entries", "symbol", "meaning").join(
        symbols.unique(), left_on=["fact_id", "symbol"], right_on=["fact_id", "used"], how="anti"
    )
    return RuleQuery.integer(
        relations.counted(stale),
        pl.col("value"),
        findings=FindingQuery.build(
            stale,
            pl.concat_str(
                pl.lit("the notation index lists `"),
                pl.col("symbol"),
                pl.lit("` as `"),
                pl.col("meaning").str.slice(0, 60),
                pl.lit("` and the body never sets it"),
            ),
            (("index rows the body dropped", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
