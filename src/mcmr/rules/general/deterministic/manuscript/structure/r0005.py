from collections.abc import Sequence

import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0005", policy=Numeric())
def numbered_statement_nothing_refers_to(
    subject: Table[ManuscriptFact],
    *,
    ignored_kinds: Sequence[str] = ("example", "remark"),
) -> CountQuery:
    """Count labelled statements no cross reference ever names.

    Definition
    ----------
    A numbered statement is numbered so the rest of the document can point at it. Report a
    statement that declares a cross reference target which no reference anywhere in the manuscript
    names. A statement kind in `ignored_kinds` is illustrative rather than load bearing, and is
    left alone.

    This is a measurement rather than a defect, because a statement can be worth numbering for the
    reader's own navigation even when nothing points at it. What the number is worth is a judgment
    about how the document is meant to be read, so a project states its own ceiling.

    Evidence
    --------
    Each finding names the statement kind, its label, and where it sits. The value is the number
    of labelled statements no reference names.

    Exceptions
    ----------
    A statement referenced only by name in prose, as `the trichotomy theorem`, is reported here
    because no machine can follow that pointer, and the repair is usually to reference it properly
    rather than to exclude it. A defensive label a project adds ahead of writing the section that
    will use it is reported until that section is written.

    Examples
    --------
    Bad
    ~~~
    A `lemma` carrying `\\label{lem:ensemble}` that nothing references returns `1`.

    Good
    ~~~~
    The same lemma referenced once anywhere returns `0`, and an unlabelled statement is never
    counted at all.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, cross references
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    orphaned = relations.labelled("statements", "kind").filter(
        (pl.col("label").str.len_chars() > 0)
        & (pl.col("reference_count") == 0)
        & ~pl.col("kind").is_in(list(ignored_kinds))
    )
    return RuleQuery.integer(
        relations.counted(orphaned),
        pl.col("value"),
        findings=FindingQuery.build(
            orphaned,
            pl.concat_str(
                pl.lit("`"),
                pl.col("kind"),
                pl.lit("` `"),
                pl.col("label"),
                pl.lit("` is numbered and nothing points at it"),
            ),
            (("unreferenced statements", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
