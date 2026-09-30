import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptNotationFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0009", policy=Numeric(maximum=0))
def symbol_introduced_under_two_meanings(
    subject: Table[ManuscriptNotationFact],
) -> CountQuery:
    """Count symbols assigned different explicit roles across sections without declared senses.

    Definition
    ----------
    One symbol carrying two meanings is the defect a cold reader loses the most time to, because
    nothing tells them the meaning changed. Compare explicit role phrases such as `let K denote
    the reduction depth`, and noun phrases set in apposition such as `the byte budget $\\beta$`
    or `at radix $\\beta=2$`, after normalizing case, whitespace, and a leading article. An
    apposition names only a span that is its symbol alone or that symbol stated by a relation,
    and only a run of at most three plain words opened by an article or preposition. Report two
    different such roles, even within one section, when the notation index
    separates no senses. Identical definitions and same-meaning reminders do not create a second
    role. An equality alone supplies no evidence that the symbol's meaning changed.

    Literal sum/product and quantifier binders, function-definition parameters, and declarations
    inside proofs or asserting statements are local. They do not redefine the document-wide role.

    An index row that says `elsewhere`, `instead`, or otherwise names a second sense has declared
    the reuse, and a declared reuse is a convention rather than a trap.

    Evidence
    --------
    Each finding names the symbol, its distinct normalized role phrases, and how many sections
    introduce them. The value is the number of potential undeclared meaning changes.

    Exceptions
    ----------
    Different words can express the same meaning. These findings therefore require author review,
    not automatic renaming. Arbitrary semantic equivalence, macro-generated binders, and complex
    dependent or nested binding scopes are unsupported. A declaration whose role cannot be
    extracted is not evidence of a conflict; it remains visible in the introduction facts.

    Examples
    --------
    Bad
    ~~~
    `$K$` introduced as a reduction depth in chapter one and as a kernel matrix in chapter two,
    with one index row, returns `1`, and so do `At radix $\\beta=2$` and `The byte budget
    $\\beta\\in\\mathbb N$` under one index row for `$\\beta$`.

    Good
    ~~~~
    The same `$K$` whose index row reads `Also, in \\Cref{def:gemm}, the reduction depth` returns
    `0`, and so does a symbol introduced once.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, notation
    Cites "Mathematical Writing", Knuth, Larrabee and Roberts, one meaning per symbol
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    sites = (
        relations.located("sites", "symbol", "meaning", "is_local")
        .filter(~pl.col("is_local") & (pl.col("meaning") != ""))
        .group_by("fact_id", "symbol", maintain_order=True)
        .agg(
            pl.col("section_number").n_unique().cast(pl.UInt64).alias("section_count"),
            pl.col("meaning").n_unique().alias("meaning_count"),
            pl.col("meaning").unique().sort().str.join(" | ").alias("meanings"),
            pl.col("reading_order").min().alias("reading_order"),
            pl.col("path").first(),
            pl.col("start_line").first(),
            pl.col("start_column").first(),
            pl.col("end_line").first(),
            pl.col("end_column").first(),
        )
    )
    declared = (
        relations.located("entries", "symbol", "sense_count")
        .group_by("fact_id", "symbol", maintain_order=True)
        .agg(pl.col("sense_count").max().alias("declared_senses"))
    )
    collided = (
        sites.join(declared, on=["fact_id", "symbol"], how="left")
        .with_columns(pl.col("declared_senses").fill_null(1))
        .filter((pl.col("meaning_count") >= 2) & (pl.col("declared_senses") < 2))
    )
    return RuleQuery.integer(
        relations.counted(collided),
        pl.col("value"),
        findings=FindingQuery.build(
            collided,
            pl.concat_str(
                pl.lit("`"),
                pl.col("symbol"),
                pl.lit("` has distinct declared roles in "),
                pl.col("section_count").cast(pl.String),
                pl.when(pl.col("section_count") == 1)
                .then(pl.lit(" section: "))
                .otherwise(pl.lit(" sections: ")),
                pl.col("meanings"),
                pl.lit("; the index separates no senses"),
            ),
            (("undeclared symbol reuses", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
