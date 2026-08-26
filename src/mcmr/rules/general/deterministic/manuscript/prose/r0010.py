import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0010", policy=Numeric(maximum=0))
def sentence_longer_than_a_reader_holds(
    subject: Table[ManuscriptFact],
    *,
    maximum_words: PositiveInt = 48,
) -> CountQuery:
    """Count sentences longer than a reader can hold in one pass.

    Definition
    ----------
    Split the running prose into sentences, keeping a decimal point, an initial and an
    abbreviation inside the word they belong to, and standing one placeholder in for each span of
    mathematics so a formula counts as the one word a reader reads it as. Report a sentence longer
    than `maximum_words`.

    The ceiling is set from a published paper in this field whose longest sentence is forty four
    words, so a manuscript matching that standard reports nothing and one that has grown a
    subordinate clause too many reports exactly where.

    Evidence
    --------
    Each finding names the file and line, the length, and the opening of the sentence. The value
    is the number of sentences over the ceiling.

    Exceptions
    ----------
    Prose inside table cells is measured as prose and can read long where a cell holds a whole
    clause, which is why cell text is dropped before anything is counted. A caption is measured
    with the body. A long sentence that is a list rendered as prose is reported, and the repair is
    a list rather than a shorter sentence.

    Examples
    --------
    Bad
    ~~~
    A sixty word sentence carrying four subordinate clauses returns `1`.

    Good
    ~~~~
    A document whose longest sentence runs forty four words returns `0`.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, sentence length
    Cites "The Elements of Style", Strunk and White, omit needless words
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    paragraphs = relations.located("paragraphs", "in_cells").select(
        "fact_id", pl.col("reading_order").alias("paragraph_order"), "in_cells"
    )
    sentences = relations.located("sentences", "word_count", "text").join(
        paragraphs,
        left_on=["fact_id", "reading_order"],
        right_on=["fact_id", "paragraph_order"],
        how="left",
    )
    long = sentences.filter(
        (pl.col("word_count") > maximum_words) & ~pl.col("in_cells").fill_null(False)
    )
    return RuleQuery.integer(
        relations.counted(long),
        pl.col("value"),
        findings=FindingQuery.build(
            long,
            pl.concat_str(
                pl.lit("a sentence of "),
                pl.col("word_count").cast(pl.String),
                pl.lit(" words opens `"),
                pl.col("text").str.slice(0, 60),
                pl.lit("`"),
            ),
            (("overlong sentences", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
