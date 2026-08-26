from collections.abc import Sequence

import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0003", policy=Numeric(maximum=0))
def term_used_before_it_is_marked(
    subject: Table[ManuscriptNotationFact],
    *,
    marking_commands: Sequence[str] = ("term",),
    minimum_uses: PositiveInt = 2,
) -> CountQuery:
    """Count terms a reader meets in prose before the manuscript marks them.

    Definition
    ----------
    A manuscript introduces a name by setting it apart, and every project spells that with one or
    two commands. Read each phrase marked by a command in `marking_commands`, then read the body
    prose in order and find where that phrase is first used. Report a phrase used at least
    `minimum_uses` times whose first use comes before the mark that introduces it.

    Marking is the only signal available here, which is why the setting exists. A project that
    introduces terms with a bold or an emphasis command adds that command to `marking_commands`
    and gets the same answer, at the cost of every phrase it sets bold for stress.

    A use is counted as a whole word, so `state` is not found inside `statement`.

    Evidence
    --------
    Each finding names the term, the file and line where the reader first meets it, and where the
    manuscript eventually marks it. The value is the number of terms used before they are marked.

    Exceptions
    ----------
    A phrase marked for stress rather than for definition is the false positive this rule trades
    for its precision, which is why `marking_commands` defaults to the two commands a definition
    is usually set in rather than to every emphasis command. A term the manuscript never marks at
    all is invisible here, and that is the larger family of the same defect, so a reader who finds
    an undefined word should not read a passing run as proof there are none. A phrase shorter than
    four characters or longer than four words is not read as a term.

    Examples
    --------
    Bad
    ~~~
    A chapter two scope clause reading `with no systematic absorption` where `\\term{absorption}`
    is marked in chapter four returns `1`.

    Good
    ~~~~
    A term marked on its first appearance returns `0`, and so does one the manuscript uses once.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, definitions
    Cites "The Elements of Style", Strunk and White, terms of art
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    terms = relations.located(
        "terms", "term", "command", "mark_order", "first_use_order", "use_count"
    )
    early = terms.filter(
        pl.col("command").is_in(list(marking_commands))
        & (pl.col("use_count") >= minimum_uses)
        & (pl.col("first_use_order") > 0)
        & (pl.col("first_use_order") < pl.col("mark_order"))
    )
    return RuleQuery.integer(
        relations.counted(early),
        pl.col("value"),
        findings=FindingQuery.build(
            early,
            pl.concat_str(
                pl.lit("`"),
                pl.col("term"),
                pl.lit("` is used before `\\"),
                pl.col("command"),
                pl.lit("` marks it, "),
                pl.col("use_count").cast(pl.String),
                pl.lit(" uses in all"),
            ),
            (("terms used before marking", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("first_use_order"),
        ),
    )
