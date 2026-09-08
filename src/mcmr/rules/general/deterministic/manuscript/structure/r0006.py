import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0006", policy=Numeric(maximum=0))
def float_without_a_text_reference(
    subject: Table[ManuscriptFact],
) -> CountQuery:
    """Count labeled figures and tables that the text never references.

    Definition
    ----------
    Report a labeled figure or table that no text references. The object may appear before its
    numbered discussion; it does not need a forward reference to announce it. Reading order is
    checked separately by ALL-MANU0001.

    Evidence
    --------
    Each finding names the float kind and its label. The value is the number of unreferenced
    labeled floats.

    Exceptions
    ----------
    An unlabeled decorative figure declares no target and is not counted. Caption text is not
    running prose, so a self-reference inside a caption does not establish a text reference.

    Examples
    --------
    Bad
    ~~~
    A `table` carrying `\\label{tab:survival}` that nothing references returns `1`.

    Good
    ~~~~
    A table discussed by the paragraph below it returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, tables and figures
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    floats = relations.labelled("floats", "kind").filter(pl.col("label").str.len_chars() > 0)
    unread = floats.filter(pl.col("reference_count") == 0)
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
                pl.lit("` is never referenced"),
            ),
            (("unreferenced floats", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
