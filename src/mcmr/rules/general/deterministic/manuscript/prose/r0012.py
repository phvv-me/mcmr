from collections.abc import Sequence

import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table

# The words a heading opens with when it has stopped naming a thing and started making a claim.
_OPENERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "which",
    "who",
    "is",
    "are",
    "does",
    "do",
    "can",
    "should",
    "must",
    "will",
)


@rule("ALL-MANU0012", policy=Numeric(maximum=0))
def section_title_that_is_not_a_noun_phrase(
    subject: Table[ManuscriptFact],
    *,
    openers: Sequence[str] = _OPENERS,
    maximum_words: PositiveInt = 6,
) -> CountQuery:
    """Count headings phrased as a question or as an answer to one.

    Definition
    ----------
    A heading names the thing under it, which is what lets a reader scan a contents page and
    decide where to go. A heading that asks a question, or answers one, is a sentence the reader
    has to read rather than a name they can recognize, and it is what a document grows when it is
    written by accretion. Report a heading ending in a question mark, opening with a word in
    `openers`, or running longer than `maximum_words` words.

    Evidence
    --------
    Each finding names the heading and which of the three shapes it takes. The value is the number
    of headings that are not noun phrases.

    Exceptions
    ----------
    A heading opening with a gerund, such as `Mapping implementations to trees`, names an activity
    and passes, which is why the opener list holds interrogatives and auxiliaries rather than every
    verb. A title carrying a symbol counts that symbol as one word. A conference template that
    fixes a long section name is a reason to exclude the file rather than to raise the ceiling.

    Examples
    --------
    Bad
    ~~~
    `What does batching actually change?` returns `1`, and so does
    `Why the tax and the divergence index are siblings`.

    Good
    ~~~~
    `Conditional second-moment model` returns `0`, and so does `Extremal trees`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, section headings
    Cites "The Elements of Style", Strunk and White, headings
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    sections = relations.located("sections", "title", "title_word_count", "level")
    opener = pl.col("title").str.to_lowercase().str.split(" ").list.first()
    asks = pl.col("title").str.ends_with("?")
    answers = opener.is_in([word.lower() for word in openers])
    sprawls = pl.col("title_word_count") > maximum_words
    reported = sections.filter(asks | answers | sprawls)
    return RuleQuery.integer(
        relations.counted(reported),
        pl.col("value"),
        findings=FindingQuery.build(
            reported,
            pl.concat_str(
                pl.lit("the heading `"),
                pl.col("title"),
                pl.lit("` "),
                pl.when(asks)
                .then(pl.lit("asks a question"))
                .when(answers)
                .then(pl.lit("answers one"))
                .otherwise(pl.lit("reads as a sentence")),
            ),
            (("headings that are not names", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
