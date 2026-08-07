from typing import TYPE_CHECKING, cast

from mcmr.domain.contracts import RuleContract, RuleSetting, RuleValue
from mcmr.facts import LiteralGroupFact
from mcmr.query import RuleQuery, scalar_frame_value
from mcmr.rules.general import module_repeated_string_literal
from mcmr.table import AnalysisSession

if TYPE_CHECKING:
    from pathlib import Path

    from mcmr.plugins import Fact, Table

# One module and five strings, each landing on a different side of this rule.
_SUBJECT = '''"""One repeated docstring."""


def publish(topic):
    """One repeated docstring."""
    return topic


def archive(topic):
    """One repeated docstring."""
    return topic


def retry(topic):
    """One repeated docstring."""
    return topic


def route(record):
    chosen = "audit-events"
    fallback = "audit-events"
    known = ("audit-events", "audit-events")
    padded = ("short", "short", "short", "short")
    nearly = ("almost-there", "almost-there", "almost-there")
    publish(topic="column-name")
    archive(topic="column-name")
    retry("column-name")
    retry("column-name")
    if record == "audit-events" or record.parent == "audit-events":
        return chosen, fallback, known, padded, nearly
    return None
'''


def literal_table(root: Path) -> Table[LiteralGroupFact]:
    """Parse one corpus module into the grouped literal relations."""
    (root / "subject.py").write_text(_SUBJECT, encoding="utf-8")
    return AnalysisSession(root, suffixes=[".py"], typed_families=[LiteralGroupFact]).table(
        LiteralGroupFact
    )


def query(
    table: Table[LiteralGroupFact],
    rule: RuleContract,
    **settings: RuleSetting,
) -> RuleQuery:
    """Invoke one literal rule once over the whole corpus."""
    result = rule.invoke_table(cast("Table[Fact]", table), settings=settings, dependencies={})
    if not isinstance(result, RuleQuery):
        raise TypeError("a deterministic literal rule returned a model query")
    return result


def total(
    table: Table[LiteralGroupFact],
    rule: RuleContract,
    **settings: RuleSetting,
) -> RuleValue:
    """Return the single corpus scalar one literal rule answers with."""
    return scalar_frame_value(query(table, rule, **settings).values.collect())


def messages(
    table: Table[LiteralGroupFact],
    rule: RuleContract,
    **settings: RuleSetting,
) -> list[str]:
    """Return every finding message one invocation states."""
    findings = query(table, rule, **settings).findings
    assert findings is not None
    return findings.rows.collect().get_column("message").to_list()


def test_a_literal_one_module_states_six_times_is_reported_with_its_count(
    tmp_path: Path,
) -> None:
    """The reported literal is quoted beside how often the module spells it.

    `audit-events` is the decision this module made and never named, and it reaches the count by
    two assignments, two collection elements, and two equality tests.
    """
    table = literal_table(tmp_path)

    assert total(table, module_repeated_string_literal) == 1
    assert messages(table, module_repeated_string_literal) == [
        "`audit-events` is written 6 times in this module"
    ]


def test_a_short_literal_and_a_third_copy_stay_below_their_own_floor(tmp_path: Path) -> None:
    """Each threshold excludes on its own, and lowering either one admits exactly its case."""
    table = literal_table(tmp_path)

    assert total(table, module_repeated_string_literal, minimum_occurrences=3) == 2
    assert total(table, module_repeated_string_literal, minimum_length=5) == 2
    assert "`short` is written 4 times in this module" in messages(
        table, module_repeated_string_literal, minimum_length=5
    )


def test_prose_and_text_handed_to_a_callable_are_never_the_modules_own_value(
    tmp_path: Path,
) -> None:
    """A docstring documents and an argument belongs to the callee, so neither joins a count."""
    table = literal_table(tmp_path)

    stated = messages(table, module_repeated_string_literal, minimum_occurrences=2)

    assert total(table, module_repeated_string_literal, minimum_occurrences=2) == 2
    assert not [message for message in stated if "repeated docstring" in message]
    assert not [message for message in stated if "column-name" in message]
