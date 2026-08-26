import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptEvidenceFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0014", policy=Numeric(maximum=0))
def ratio_published_without_its_parts(
    subject: Table[ManuscriptEvidenceFact],
    *,
    minimum_digits: PositiveInt = 3,
    minimum_parts: PositiveInt = 3,
) -> CountQuery:
    """Count ratios printed without the two numbers they are a ratio of.

    Definition
    ----------
    A share, a fraction or a ratio is a number a reader cannot check, because two different pairs
    of measurements give the same quotient and only one of them is the one that was taken. Report
    a number of at least `minimum_digits` digits printed in running prose whose sentence names it
    as a derived quantity and which shares that sentence with fewer than `minimum_parts` numbers
    in total.

    Requiring three numbers in the sentence is requiring the quotient beside its numerator and its
    denominator, which is what lets a reader divide and agree.

    Evidence
    --------
    Each finding names the number and how many numbers its sentence carries. The value is the
    number of derived quantities published without their parts.

    Exceptions
    ----------
    A ratio whose parts sit in the previous sentence is reported, and moving them into the same
    sentence or into a table is the repair. A ratio printed in a table cell is never counted,
    since the columns beside it are its parts. A sentence naming a ratio without printing one, as
    a definition does, states no number and reports nothing.

    Examples
    --------
    Bad
    ~~~
    A sentence reading `the discrete share is 0.145584` returns `1`.

    Good
    ~~~~
    `the discrete share is 0.145584, from 2.5844 against 15.9974` returns `0`, and a table cell
    holding the same share returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, reporting numbers
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    bare = relations.located(
        "numbers", "literal", "in_cells", "names_ratio", "sentence_number_count"
    ).filter(
        ~pl.col("in_cells")
        & pl.col("names_ratio")
        & (pl.col("literal").str.count_matches(r"[0-9]") >= minimum_digits)
        & (pl.col("sentence_number_count") < minimum_parts)
    )
    return RuleQuery.integer(
        relations.counted(bare),
        pl.col("value"),
        findings=FindingQuery.build(
            bare,
            pl.concat_str(
                pl.lit("`"),
                pl.col("literal"),
                pl.lit("` is named as a derived quantity beside "),
                (pl.col("sentence_number_count") - 1).cast(pl.String),
                pl.lit(" other numbers"),
            ),
            (("ratios without their parts", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
