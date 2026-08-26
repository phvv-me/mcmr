from typing import cast

from mcmr.domain.contracts import RuleContract, RuleSetting, RuleValue
from mcmr.facts import Fact, SourceSpan
from mcmr.plugins import RepositoryTables
from mcmr.query import RuleQuery, scalar_frame_value
from mcmr.table import fact_table


def manuscript[FactT: Fact](family: type[FactT], **records: object) -> FactT:
    """Return one located manuscript fact of the requested family."""
    return family.model_validate(
        {"key": family.__name__, "span": SourceSpan(path="paper.tex"), "root": "paper.tex"}
        | records
    )


def measured(rule: RuleContract, *subjects: Fact, **settings: RuleSetting) -> RuleValue:
    """Run one rule over the facts it names and return its single scalar."""
    return scalar_frame_value(reported(rule, *subjects, **settings).values.collect())


def messages(rule: RuleContract, *subjects: Fact, **settings: RuleSetting) -> list[str]:
    """Return the finding messages one rule reports, in the order it reports them."""
    findings = reported(rule, *subjects, **settings).findings
    if findings is None:
        raise TypeError("a manuscript rule reported no finding relation")
    return cast("list[str]", findings.rows.collect().get_column("message").to_list())


def reported(rule: RuleContract, *subjects: Fact, **settings: RuleSetting) -> RuleQuery:
    """Invoke one rule over one table per fact family it declares."""
    tables = {type(subject): fact_table(type(subject), [subject]) for subject in subjects}
    result = rule.invoke(
        RepositoryTables(cast("dict", tables)), settings=settings, dependencies={}
    )
    if not isinstance(result, RuleQuery):
        raise TypeError("a deterministic manuscript rule returned a model query")
    return result
