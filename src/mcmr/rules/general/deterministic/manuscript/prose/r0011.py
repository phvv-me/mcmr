import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0011", policy=Numeric(maximum=0))
def paragraph_longer_than_a_reader_holds(
    subject: Table[ManuscriptFact],
    *,
    maximum_words: PositiveInt = 200,
    maximum_sentences: PositiveInt = 12,
) -> CountQuery:
    """Count paragraphs carrying more than one idea a reader can follow.

    Definition
    ----------
    A paragraph is what a blank line separates. Report one longer than `maximum_words` words or
    holding more than `maximum_sentences` sentences, measuring only the running prose of the body
    and never the contents of a table cell or a float.

    Both ceilings come from a published paper in this field whose longest paragraph runs one
    hundred and seventy six words over eleven sentences, so a manuscript written to that standard
    reports nothing.

    Evidence
    --------
    Each finding names the file and line the paragraph opens at, its word count and its sentence
    count. The value is the number of paragraphs over either ceiling.

    Exceptions
    ----------
    A paragraph inside a table cell or a float caption is never counted, since neither is read at
    the pace running prose is. A long paragraph that is really an enumeration is reported, and the
    repair is to enumerate it. An abstract written as one dense paragraph is reported like any
    other, which is usually right.

    Examples
    --------
    Bad
    ~~~
    A paragraph of three hundred words returns `1`, and so does one of fourteen short sentences.

    Good
    ~~~~
    A paragraph of forty six words over three sentences returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, paragraphs
    Cites "The Elements of Style", Strunk and White, one paragraph one topic
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    paragraphs = relations.located(
        "paragraphs", "word_count", "sentence_count", "in_cells", "in_float"
    )
    long = paragraphs.filter(
        ~pl.col("in_cells")
        & ~pl.col("in_float")
        & ((pl.col("word_count") > maximum_words) | (pl.col("sentence_count") > maximum_sentences))
    )
    return RuleQuery.integer(
        relations.counted(long),
        pl.col("value"),
        findings=FindingQuery.build(
            long,
            pl.concat_str(
                pl.lit("a paragraph of "),
                pl.col("word_count").cast(pl.String),
                pl.lit(" words over "),
                pl.col("sentence_count").cast(pl.String),
                pl.lit(" sentences"),
            ),
            (("overlong paragraphs", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
