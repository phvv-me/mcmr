from pathlib import Path
from typing import TYPE_CHECKING

from mcmr.domain.contracts import RuleContract, RuleSetting, RuleValue
from mcmr.facts import SyntaxFact, TryBlockFact
from mcmr.query import RuleQuery, scalar_frame_value
from mcmr.table import AnalysisSession, RepositoryTables, SyntaxRelation

if TYPE_CHECKING:
    from collections.abc import Mapping


def table(root: Path, sources: Mapping[str, str]) -> RepositoryTables:
    """Parse one multilingual error corpus into native syntax relations."""
    for name, source in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    session = AnalysisSession(
        root,
        suffixes=sorted({Path(name).suffix for name in sources}),
        typed_families=(SyntaxFact, TryBlockFact),
    )
    return RepositoryTables().add(session.syntax_tables()).add(session.table(TryBlockFact))


def query(
    rule: RuleContract,
    subject: RepositoryTables,
    **settings: RuleSetting,
) -> RuleQuery:
    """Invoke one error rule once over every declaration in the repository table."""
    result = rule.invoke(
        subject,
        settings=settings,
        dependencies={},
    )
    if not isinstance(result, RuleQuery):
        raise TypeError("a deterministic error rule returned a model query")
    return result


def value(result: RuleQuery, subject: RepositoryTables, qualname: str) -> RuleValue:
    """Return one declaration's scalar from a completed repository query."""
    facts = subject[SyntaxFact].frame(SyntaxRelation.FACTS).select("fact_id", "qualname")
    values = result.values.collect().join(facts, on="fact_id")
    return scalar_frame_value(values.filter(values["qualname"] == qualname))
