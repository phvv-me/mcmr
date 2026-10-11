from typing import TYPE_CHECKING

import pytest

from mcmr.facts import ManuscriptFact, ManuscriptSentence

from .support import manuscript, measured

if TYPE_CHECKING:
    from mcmr.domain.contracts import RuleContract
    from mcmr.rulebook.catalog import Catalog


@pytest.fixture
def sentence_rule(catalog: Catalog) -> RuleContract:
    """Exercise the sentence rule discovered by the same catalog that runs repository checks."""
    return next(rule for rule in catalog.rules if rule.id == "ALL-MANU0010")


def test_sentence_bounds_reject_an_inverted_range(sentence_rule: RuleContract) -> None:
    """An impossible interval fails before it can report every sentence as defective."""
    with pytest.raises(ValueError, match="minimum_words must not exceed maximum_words"):
        measured(
            sentence_rule,
            manuscript(ManuscriptFact),
            minimum_words=49,
            maximum_words=48,
        )


@pytest.mark.parametrize("word_count, outside", [(9, True), (10, False), (48, False), (49, True)])
def test_sentence_bounds_include_both_endpoints(
    sentence_rule: RuleContract, word_count: int, *, outside: bool
) -> None:
    """The accepted interval includes its floor and ceiling, but neither neighboring length."""
    fact = manuscript(
        ManuscriptFact,
        sentences=[ManuscriptSentence(word_count=word_count, text="Words in a sentence.")],
    )

    assert measured(sentence_rule, fact) == int(outside)
