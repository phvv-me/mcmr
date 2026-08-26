from collections.abc import Sequence

import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table

# What a reference points at when the reader has to have understood it already.
_HELD = ("theorem", "lemma", "proposition", "corollary", "definition")


@rule("ALL-MANU0001", policy=Numeric(maximum=0))
def forward_reference_to_unread_material(
    subject: Table[ManuscriptFact],
    *,
    kinds: Sequence[str] = _HELD,
    marked_commands: Sequence[str] = ("autoref", "nameref"),
) -> CountQuery:
    """Count references sending a reader to something they have not read yet.

    Definition
    ----------
    Compare every cross reference against the reading order of the label it names, assembled by
    splicing each included file in where the including file put it. Report a reference whose
    target appears later than the reference itself and whose target kind begins with one of
    `kinds`. A reader executes a document once, from the top, so a reference forward is a demand
    to hold an unread thing in mind, and it is the complaint a cold reader makes most often.

    Only the kinds a reader has to have understood are held to this, which by default is the
    numbered statements and not the sections, because a roadmap paragraph naming every chapter
    ahead is how a document is supposed to open. A spelling in `marked_commands` names its target
    in words rather than by number, which is how a deliberate forward pointer is written, so those
    are read as marked and stay quiet.

    Evidence
    --------
    Each finding names the reference, the file and line it sits on, the target it points at, and
    where in the document that target is first read. The value is the number of forward
    references into material the reader has not reached.

    Exceptions
    ----------
    A reference to a figure, a table or an equation is never reported, because a float is placed
    by the typesetter rather than by the author. A reference naming a label the manuscript never
    declares resolves to nothing and is left to the build, since a broken reference is a different
    defect. A section is out of scope by default and a project that wants its own reading order
    held to this adds `section` to `kinds`, which is the stricter reading and reports every
    roadmap sentence.

    Examples
    --------
    Bad
    ~~~
    A chapter one sentence reading `as \\Cref{thm:duality} shows` where `thm:duality` is declared
    in chapter five returns `1`.

    Good
    ~~~~
    The same sentence pointing at `fig:chain` returns `0`, and so does any reference to a theorem
    the reader has already passed.

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
