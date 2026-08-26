from collections.abc import Sequence

import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0002", policy=Numeric(maximum=0))
def symbol_used_before_it_is_introduced(
    subject: Table[ManuscriptNotationFact],
    *,
    minimum_uses: PositiveInt = 3,
    ignored: Sequence[str] = ("i", "j", "k", "n", "x", "y", "z"),
) -> CountQuery:
    """Count symbols a reader meets before the manuscript says what they are.

    Definition
    ----------
    Read every math span in reading order, keeping each symbol as the reader spells it, subscript
    and all. A span introduces a symbol when the symbol stands alone on the left of an equality
    set as a display, or when the words immediately before the span are a definition cue such as
    `let`, `where`, `with` or `denote`. Report a symbol used at least `minimum_uses` times whose
    first use comes before its first introduction, and a symbol used that often with no
    introduction anywhere.

    A symbol named in `ignored` is a bound index a reader reads locally and never looks up, so
    those are dropped before anything is counted. A symbol the manuscript's own notation index
    lists is introduced by that index whatever the body does, so it is dropped too, which leaves
    this rule reporting the symbols nothing anywhere introduces.

    Evidence
    --------
    Each finding names the symbol, where the reader first meets it, and where the manuscript
    introduces it, or says that it never does. The value is the number of symbols used before
    they are introduced.

    Exceptions
    ----------
    A symbol used fewer than `minimum_uses` times is local to the passage that spells it, so it is
    left alone. A symbol introduced by a macro rather than in prose is invisible to a reader of
    the source and is reported, which is the honest answer since the printed document introduces
    it nowhere either. An abstract that names a symbol and points at the section defining it is
    reported here and is the one shape worth an exclusion, since the pointer does the work.

    Examples
    --------
    Bad
    ~~~
    `$\\nu$` used in the abstract and in chapter one, first written as `$\\nu = \\dots$` in
    chapter five, returns `1`.

    Good
    ~~~~
    `$\\nu$` introduced by `let $\\nu$ denote` on its first appearance returns `0`, and so does
    a `$k$` that only ever indexes a sum.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, notation
    Cites "Mathematical Writing", Knuth, Larrabee and Roberts, defining symbols
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    symbols = relations.located("symbols", "name", "use_count", "first_order").filter(
        (pl.col("use_count") >= minimum_uses) & ~pl.col("name").is_in(list(ignored))
    )
    introductions = (
        relations.located("sites", "symbol")
        .group_by("fact_id", "symbol", maintain_order=True)
        .agg(pl.col("reading_order").min().alias("introduced_order"))
    )
    indexed = relations.located("entries", "symbol").select(
        "fact_id", pl.col("symbol").alias("name")
    )
    unintroduced = (
        symbols.join(
            introductions, left_on=["fact_id", "name"], right_on=["fact_id", "symbol"], how="left"
        )
        .join(indexed.unique(), on=["fact_id", "name"], how="anti")
        .filter(
            pl.col("introduced_order").is_null()
            | (pl.col("first_order") < pl.col("introduced_order"))
        )
    )
    return RuleQuery.integer(
        relations.counted(unintroduced),
        pl.col("value"),
        findings=FindingQuery.build(
            unintroduced,
            pl.concat_str(
                pl.lit("`"),
                pl.col("name"),
                pl.lit("` is used "),
                pl.col("use_count").cast(pl.String),
                pl.lit(" times and is introduced "),
                pl.when(pl.col("introduced_order").is_null())
                .then(pl.lit("nowhere"))
                .otherwise(pl.lit("only after the reader has met it")),
            ),
            (("symbols used before introduction", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("first_order"),
        ),
    )
