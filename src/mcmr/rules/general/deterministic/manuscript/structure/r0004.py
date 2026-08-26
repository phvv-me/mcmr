from collections.abc import Sequence

import polars as pl

from ...... import Numeric, rule
from ......domain.contracts import Unit
from ......facts import ManuscriptFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import ManuscriptRelations, Table


@rule("ALL-MANU0004", policy=Numeric(maximum=0))
def numbered_statement_left_without_an_argument(
    subject: Table[ManuscriptFact],
    *,
    discharge_heads: Sequence[str] = ("proof", "why", "sketch", "argument", "derivation"),
    unproved_kinds: Sequence[str] = ("conjecture", "assumption", "problem", "question"),
) -> CountQuery:
    """Count asserting statements the manuscript never argues.

    Definition
    ----------
    Read the preamble to learn which environments this manuscript declares as numbered statements
    and which of them assert rather than name, which is what a plain theorem style means. For each
    asserting statement, look at what immediately follows it. Report one that is followed by no
    proof environment and by no run-in head opening with a word in `discharge_heads`.

    A house that argues its theorems with a bold `Why it is true.` rather than with a proof
    environment satisfies this, because the head is read as well as the environment. An
    environment named in `unproved_kinds` asserts something nobody claims to have shown, so it
    owes nothing.

    Evidence
    --------
    Each finding names the statement kind, its label, and the opening words of whatever followed
    it. The value is the number of asserting statements with no argument attached.

    Exceptions
    ----------
    A statement argued by the paragraph immediately before it rather than after is reported, and
    that is a real style some manuscripts use, so a project writing that way states its own
    ceiling rather than tuning the rule. A proof deferred to an appendix satisfies the rule when
    the sentence after the statement says so, since that sentence opens with a discharge head, and
    is reported when nothing says so, which is the case worth reporting.

    Examples
    --------
    Bad
    ~~~
    A `theorem` followed straight by the next section returns `1`.

    Good
    ~~~~
    A `theorem` followed by `\\begin{proof}` returns `0`, and so does one followed by
    `Why it is true.` A `conjecture` returns `0` whatever follows it.

    References
    ----------
    Cites "Handbook of Writing for the Mathematical Sciences", Higham, theorems and proofs
    Cites "Mathematical Writing", Knuth, Larrabee and Roberts, proofs
    https://arxiv.org/abs/2607.18758
    """
    relations = ManuscriptRelations(subject)
    statements = relations.located(
        "statements", "kind", "label", "owes_proof", "proof_order", "discharge_head"
    )
    head = pl.col("discharge_head").fill_null("").str.to_lowercase().str.strip_chars()
    argued = pl.any_horizontal(*(head.str.starts_with(word) for word in discharge_heads))
    unargued = statements.filter(
        pl.col("owes_proof")
        & ~pl.col("kind").is_in(list(unproved_kinds))
        & (pl.col("proof_order") == 0)
        & ~argued
    )
    return RuleQuery.integer(
        relations.counted(unargued),
        pl.col("value"),
        findings=FindingQuery.build(
            unargued,
            pl.concat_str(
                pl.lit("`"),
                pl.col("kind"),
                pl.lit("` `"),
                pl.col("label"),
                pl.lit("` is followed by `"),
                head.str.slice(0, 40),
                pl.lit("` rather than by an argument"),
            ),
            (("statements left unargued", pl.lit(1.0), Unit.COUNT),),
            finding_order=pl.col("reading_order"),
        ),
    )
