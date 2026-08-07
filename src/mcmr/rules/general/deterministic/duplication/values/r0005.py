import polars as pl
from pydantic import NonNegativeInt

from ...... import rule
from ......domain.contracts import Unit
from ......facts import LiteralGroupFact
from ......query import CountQuery, FindingQuery, RuleQuery
from ......table import Table


@rule("ALL-DUPL0005")
def module_repeated_string_literal(
    subject: Table[LiteralGroupFact],
    *,
    minimum_occurrences: NonNegativeInt = 4,
    minimum_length: NonNegativeInt = 8,
) -> CountQuery:
    """Find one string literal a single module writes out over and over.

    Definition
    ----------
    Add up every place one module spells the exact same string and report that value once it
    reaches `minimum_occurrences` and is at least `minimum_length` characters long. A value typed
    out four times in one file is a decision the module already made and never named, so renaming
    it means finding every copy first, and missing one is the ordinary way two spellings of the
    same idea start to drift. A module constant states the decision once and gives every use the
    same name.

    Only text the module states as its own counts, which is an assignment, a return, a collection
    element, or one side of an equality test. Text handed to a callable belongs to that callable,
    because a column name, a mode flag, or a format token repeats as often as the calls that need
    it and names nothing the module decided.

    Evidence
    --------
    Each finding quotes the literal and how many times the module writes it. The value is the
    number of literals in that module that reached both thresholds.

    Exceptions
    ----------
    A string shorter than `minimum_length` stays local, because a short token is usually clearer
    where it is written than behind a name that would have to be invented for it. A docstring is
    never counted, since a statement that is nothing but a string documents the code rather than
    stating a value the program uses. Repetition spread across several modules is a different
    decision with a different owner and belongs to `ALL-DUPL0002`, which judges cross-file groups
    by their resolved syntax role. A project whose domain repeats a short token with stable
    meaning lowers `minimum_length`, and one that tolerates more copies raises
    `minimum_occurrences`. Test modules restate fixture text on purpose and are excluded by
    pointing this rule's source globs away from them rather than by guessing from a path.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       default_topic = "audit-events"
       retry_topic = "audit-events"
       known = ("audit-events", "audit-events")
       if record.topic == "audit-events":
           ...

    Good
    ~~~~
    .. code-block:: python

       AUDIT_TOPIC = "audit-events"

       default_topic = AUDIT_TOPIC
       retry_topic = AUDIT_TOPIC
       known = (AUDIT_TOPIC, AUDIT_TOPIC)
       if record.topic == AUDIT_TOPIC:
           ...

    A module stating `audit-events` four times of its own returns `1`. The same module stating it
    three times returns `0`, and so does one repeating `id` ten times, because that token is below
    the length floor. A module calling `frame.select("start_line")` in ten places returns `0`,
    because the column name belongs to the frame rather than to the module.

    References
    ----------
    Cites "Refactoring", Replace Magic Literal
    https://refactoring.com/catalog/replaceMagicLiteral.html
    Cites "The Pragmatic Programmer", the DRY principle
    Cites "PEP 8, Style Guide for Python Code", constants
    https://peps.python.org/pep-0008/#constants
    """
    relations = subject
    repeated = (
        relations.records("string_groups")
        .filter(~pl.col("is_callee_vocabulary"))
        .select("fact_id", pl.col("value").alias("literal"), "occurrence_count")
        .group_by("fact_id", "literal", maintain_order=True)
        .agg(pl.col("occurrence_count").sum().cast(pl.UInt64).alias("module_occurrences"))
        .filter(
            (pl.col("literal").str.len_chars() >= minimum_length)
            & (pl.col("module_occurrences") >= minimum_occurrences)
        )
    )
    frame = relations.counted(repeated)
    details = repeated.with_row_index("finding_order").join(
        relations.facts(), on="fact_id", how="inner"
    )
    return RuleQuery.integer(
        frame,
        pl.col("value"),
        findings=FindingQuery.build(
            details,
            pl.concat_str(
                pl.lit("`"),
                pl.col("literal"),
                pl.lit("` is written "),
                pl.col("module_occurrences"),
                pl.lit(" times in this module"),
            ),
            (("module repeated string literal", pl.lit(1), Unit.COUNT),),
            finding_order=pl.col("finding_order"),
            question=pl.concat_str(
                pl.lit("say where `"), pl.col("literal"), pl.lit("` should be named")
            ),
            options=(
                "name it once as a module constant every use reads",
                "leave the copies where each one means something different",
            ),
            evidence=pl.col("evidence"),
        ),
    )
