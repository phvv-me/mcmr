import polars as pl
from pydantic import NonNegativeInt

from ..... import rule
from .....domain.contracts import Unit
from .....facts import SyntaxFact
from .....query import FindingQuery, RuleQuery
from .....table import SyntaxRelation, Table


@rule("ALL-NAMI0001")
def uninformative_local_name(
    subject: Table[SyntaxFact],
    *,
    minimum_length: NonNegativeInt = 3,
    conventional_names: tuple[str, ...] = ("i", "j", "k", "n", "x", "y", "z", "_"),
) -> RuleQuery[int]:
    """Count local names too short to say what they hold.

    Definition
    ----------
    Read every name one declaration binds and report one shorter than `minimum_length` that is not
    one of the `conventional_names`. A local name is the cheapest documentation a body has and the
    only one that cannot go stale, so a body that binds `d`, `r`, and `tmp` has spent that budget
    on nothing and made every later line ambiguous. A name the declaration binds several times is
    reported once, at its first binding, because one rename repairs every rebinding.

    Only a callable is judged. A field on a type is part of an interface its readers meet by name
    elsewhere, so `id` on a model reads fine where `id` inside a function body does not.

    This is the first rule to read code rather than counts. It receives the declaration's own tree
    and its exact source, which is what lets it ask about spelling at all.

    Evidence
    --------
    Each finding names the declaration that holds the binding, the name itself, the line it is
    first bound on, and how many characters short of readable it is. The repair is a choice,
    because only the author knows what the value holds. The value is the number of distinct
    uninformative names the declaration binds.

    Exceptions
    ----------
    A single-letter index in a comprehension or a short loop is a convention older than the code
    and reads fine, so `conventional_names` leaves `i`, `j`, `k`, `n`, `x` through `z`, and `_`
    alone by default, and a project whose domain has its own short vocabulary names it there. A
    field declared on a type is not a local and is not judged. A name whose scope is one line is
    arguably fine too, which is why the ceiling is a setting rather than a rule.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       def load(path):
           d = read(path)
           r = parse(d)
           return r

    Good
    ~~~~
    .. code-block:: python

       def load(path):
           raw = read(path)
           return parse(raw)

    References
    ----------
    Cites "Clean Code", chapter 2, meaningful names
    Cites "Code Complete", chapter 11, the power of variable names
    Cites "PEP 8, Style Guide for Python Code", naming conventions
    https://peps.python.org/pep-0008/#naming-conventions
    """
    facts = subject.lazy(SyntaxRelation.FACTS)
    brief = (
        subject.lazy(SyntaxRelation.NODES)
        .join(
            facts.filter(pl.col("kind") == "callable").select("fact_id", "qualname"),
            on="fact_id",
            how="inner",
        )
        .filter(
            (pl.col("kind") == "binding")
            & (pl.col("name") != "")
            & (pl.col("name").str.len_chars() < minimum_length)
            & ~pl.col("name").is_in(list(conventional_names))
        )
        .unique(["fact_id", "name"], keep="first", maintain_order=True)
    )
    counts = brief.group_by("fact_id", maintain_order=True).agg(
        pl.len().cast(pl.UInt64).alias("value")
    )
    values = facts.join(counts, on="fact_id", how="left").with_columns(
        pl.col("value").fill_null(0)
    )
    findings = FindingQuery.build(
        brief,
        pl.concat_str(
            pl.lit("`"),
            pl.col("qualname"),
            pl.lit("` binds `"),
            pl.col("name"),
            pl.lit("`, which is shorter than the "),
            pl.lit(minimum_length),
            pl.lit(" characters a name needs to say what it holds"),
        ),
        (
            ("characters in the name", pl.col("name").str.len_chars(), Unit.COUNT),
            ("characters a name needs here", pl.lit(minimum_length), Unit.COUNT),
        ),
        finding_order=pl.col("ordinal"),
        question=pl.concat_str(
            pl.lit("rename `"),
            pl.col("name"),
            pl.lit("` after what it holds"),
        ),
    )
    return RuleQuery.integer(values, pl.col("value"), findings=findings)
