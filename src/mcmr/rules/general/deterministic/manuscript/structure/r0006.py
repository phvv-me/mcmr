import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0006", policy=Numeric(maximum=0))
def float_the_reader_meets_before_anything_names_it(
    subject: Table[ManuscriptFact],
) -> CountQuery:
    """Count figures and tables a reader meets before the text points at them.

    Definition
    ----------
    A float is placed where it fits on the page, so the only thing that tells a reader why it is
    there is the sentence that references it. Report a figure or table whose label no reference
    names at all, and one whose first reference comes later in reading order than the float
    itself. Both shapes leave a reader looking at evidence with nothing to read it against.

    Evidence
    --------
    Each finding names the float kind, its label, and whether nothing references it or the first
    reference arrives after it. The value is the number of floats in either shape.

    Exceptions
    ----------
    An unlabelled decorative figure declares no target and is never counted. A float placed
    deliberately ahead of its discussion, such as a summary table opening a chapter, is reported,
    and the repair is a forward-pointing sentence rather than an exclusion. A float referenced
    only from its own caption is reported, since a caption cannot introduce the float it belongs
    to.

    Examples
    --------
    Bad
    ~~~
    A `table` carrying `\\label{tab:survival}` first referenced two sections later returns `1`,
    and so does one nothing references.

    Good
    ~~~~
    A table introduced by the paragraph above it returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, tables and figures
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    floats = relations.labelled("floats", "kind").filter(pl.col("label").str.len_chars() > 0)
    unread = floats.filter(
        (pl.col("reference_count") == 0)
        | (pl.col("first_reference_order") > pl.col("reading_order"))
    )
    return RuleQuery.integer(
        relations.counted(unread),
        pl.col("value"),
        findings=FindingQuery.build(
            unread,
            pl.concat_str(
                pl.lit("`"),
                pl.col("kind"),
                pl.lit("` `"),
                pl.col("label"),
                pl.lit("` is "),
                pl.when(pl.col("reference_count") == 0)
                .then(pl.lit("never referenced"))
                .otherwise(pl.lit("first referenced after the reader meets it")),
            ),
            (("floats met unannounced", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
