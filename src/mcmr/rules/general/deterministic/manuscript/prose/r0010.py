import polars as pl
from pydantic import PositiveInt

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0010", policy=Numeric(maximum=0))
def sentence_length_outside_house_bounds(
    subject: Table[ManuscriptFact],
    *,
    minimum_words: PositiveInt = 10,
    maximum_words: PositiveInt = 48,
) -> CountQuery:
    """Count prose sentences outside the manuscript's word-count bounds.

    Definition
    ----------
    Split the running prose into sentences, keeping a decimal point, an initial and an
    abbreviation inside the word they belong to, and standing one placeholder in for each span of
    mathematics and references so each placeholder counts as one word. Report a sentence shorter
    than `minimum_words` or longer than `maximum_words`. These bounds express house style rather
    than a claim that short sentences are universally poor writing. The ten-word floor discourages
    disconnected paragraph openings, and later sentences receive the same check.

    Evidence
    --------
    Each finding names the file and paragraph line, the sentence length, its opening text, and
    whether it opens the paragraph. The value counts sentences outside either bound.

    Exceptions
    ----------
    Table cells, float content, bibliography entries, and math-only fragments are excluded.
    The shared reader excludes headings, captions, code, and list labels before this rule runs.
    Narrative sentences in list items still receive the check. No automatic padding, joining,
    or splitting is offered because changing an argument requires an author's judgment.

    Examples
    --------
    Bad
    ~~~
    `The CPU comparison matters.` returns `1`, identified as a paragraph opening when applicable.
    A sixty-word prose sentence also returns `1`.

    Good
    ~~~~
    Prose sentences containing ten through forty-eight words return `0` under the defaults.

    References
    ----------
    Project manuscript style: ten through forty-eight words per narrative sentence.
    """
    if minimum_words > maximum_words:
        raise ValueError("minimum_words must not exceed maximum_words")
    relations = ManuscriptRelations(subject)
    paragraphs = relations.located("paragraphs", "in_cells", "in_float", "in_bibliography").select(
        "fact_id",
        pl.col("reading_order").alias("paragraph_order"),
        "in_cells",
        "in_float",
        "in_bibliography",
    )
    sentences = relations.located("sentences", "word_count", "text", "index").join(
        paragraphs,
        left_on=["fact_id", "reading_order"],
        right_on=["fact_id", "paragraph_order"],
        how="left",
    )
    outside = sentences.filter(
        ((pl.col("word_count") < minimum_words) | (pl.col("word_count") > maximum_words))
        & ~pl.col("in_cells").fill_null(False)
        & ~pl.col("in_float").fill_null(False)
        & ~pl.col("in_bibliography").fill_null(False)
        & pl.col("text").str.contains(r"\p{L}")
    )
    return RuleQuery.integer(
        relations.counted(outside),
        pl.col("value"),
        findings=FindingQuery.build(
            outside,
            pl.concat_str(
                pl.when(pl.col("index") == 0)
                .then(pl.lit("a paragraph-opening sentence of "))
                .otherwise(pl.lit("a sentence of ")),
                pl.col("word_count").cast(pl.String),
                pl.lit(" words opens `"),
                pl.col("text").str.slice(0, 60),
                pl.lit("`"),
            ),
            (("sentences outside word-count bounds", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
