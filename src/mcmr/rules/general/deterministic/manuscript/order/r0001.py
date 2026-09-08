from collections.abc import Sequence

import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table

# What a reference points at when the reader has to have understood it already.
_HELD = (
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "remark",
    "example",
    "section",
    "equation",
    "figure",
    "table",
    "algorithm",
    "proof",
)


@rule("ALL-MANU0001", policy=Numeric(maximum=0))
def forward_reference_to_unread_material(
    subject: Table[ManuscriptFact],
    *,
    kinds: Sequence[str] = _HELD,
    marked_commands: Sequence[str] = (),
) -> CountQuery:
    """Count references sending a reader to something they have not read yet.

    Definition
    ----------
    Compare every cross reference against the reading order of the label it names, assembled by
    splicing each included file in where the including file put it. Report a reference whose
    target appears later than the reference itself and whose target kind begins with one of
    `kinds`. A reader executes a document once, from the top, so a reference forward is a demand
    to hold an unread thing in mind, and it is the complaint a cold reader makes most often.

    The default covers statements, sections, equations, and floats. A different reference
    command does not make unread material available: `autoref` and `nameref` follow the same
    order as `ref`. A typed `proofref` may navigate to a later proof, but only when its
    resolved target is actually a proof. It cannot exempt a prerequisite definition or theorem.
    Projects allowing explicit roadmaps can configure `kinds` or
    `marked_commands`; the default requires a linear exposition.

    Evidence
    --------
    Each finding names the reference, the file and line it sits on, the target it points at, and
    where in the document that target is first read. The value is the number of forward
    references into material the reader has not reached.

    Exceptions
    ----------
    A missing label is left to the document build. This check observes source order, not page
    placement; the rendered PDF still needs review because a typesetter can move a float.

    Examples
    --------
    Bad
    ~~~
    A chapter one sentence reading `as \\Cref{thm:duality} shows` where `thm:duality` is declared
    in chapter five returns `1`.

    Good
    ~~~~
    A reference to any labeled object the reader has already passed returns `0`.

    References
    ----------
    Cites "Mathematical Writing", Knuth, Larrabee and Roberts, forward references
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, chapter 4
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    held = pl.any_horizontal(*(pl.col("target_kind").str.starts_with(kind) for kind in kinds))
    forward = relations.resolved().filter(
        pl.col("target_order").is_not_null()
        & (pl.col("target_order") > pl.col("reading_order"))
        & held
        & ~((pl.col("command") == "proofref") & (pl.col("target_kind") == "proof"))
        & ~pl.col("command").is_in(list(marked_commands))
    )
    return RuleQuery.integer(
        relations.counted(forward),
        pl.col("value"),
        findings=FindingQuery.build(
            forward,
            pl.concat_str(
                pl.lit("`\\"),
                pl.col("command"),
                pl.lit("{"),
                pl.col("target"),
                pl.lit("}` sends the reader to a "),
                pl.col("target_kind"),
                pl.lit(" first read at `"),
                pl.col("target_path"),
                pl.lit(":"),
                pl.col("target_line"),
                pl.lit("`"),
            ),
            (("forward references", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
