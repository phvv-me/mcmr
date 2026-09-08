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
    """Count reported ratios without components or an explicit statistical definition.

    Definition
    ----------
    A quotient needs its numerator and denominator. An aggregate of per-trial ratios instead needs
    the ratio and aggregation statistic defined; a median of ratios is not a ratio of medians.
    Report a derived quantity of at least `minimum_digits` digits without `minimum_parts` numbers
    in its assembled sentence, an explicit ratio definition in the paragraph, or a linked table.
    Inline mathematics belongs to the same sentence as the surrounding words.

    Evidence
    --------
    Each finding names the number and how many numbers its sentence carries. The value is the
    number of derived quantities published without their parts.

    Exceptions
    ----------
    Formula constants and table cells are not running empirical ratio claims. A confidence bound
    is not a percentage merely because the sentence also states its confidence level. A linked
    table or literal definition provides a place to check; this rule does not prove that the table
    columns or the definition are scientifically appropriate. Implicit statistical definitions
    and definitions requiring semantic equivalence remain outside the deterministic check.

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
        "numbers",
        "literal",
        "in_cells",
        "names_ratio",
        "sentence_number_count",
        "is_mathematical",
        "has_ratio_basis",
    ).filter(
        ~pl.col("in_cells")
        & ~pl.col("is_mathematical")
        & ~pl.col("has_ratio_basis")
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
