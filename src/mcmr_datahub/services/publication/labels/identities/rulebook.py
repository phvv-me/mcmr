from .assets import flow_urn
from .keys import platform_key, slug

_RULEBOOK = "rulebook"


def category_urn(category: str) -> str:
    """Return the identity one fact group tag keeps across every run."""
    return f"urn:li:tag:{platform_key('facts', slug(category))}"


def families_urn() -> str:
    """Return the identity of the group holding every rule family term."""
    return f"urn:li:glossaryNode:{platform_key('rule', 'families')}"


def family_urn(family: str) -> str:
    """Return the identity one rule family term keeps across every run."""
    return f"urn:li:glossaryTerm:{platform_key('family', family.replace('_', '-'))}"


def lane_urn(lane: str) -> str:
    """Return the identity one execution lane tag keeps across every run."""
    return f"urn:li:tag:{platform_key(lane)}"


def property_urn(name: str) -> str:
    """Return the identity one typed property definition keeps for the whole instance.

    A structured property is declared once and reused by every codebase, so its identity is the
    qualified name under the MCMR namespace rather than anything a single repository owns.
    """
    return f"urn:li:structuredProperty:{platform_key()}.{name}"


def rule_urn(rule: str) -> str:
    """Return the one identity a rule keeps for the whole instance, whatever runs it.

    A rule is one thing. Publishing it per repository would put a copy of `ALL-DUPL0005` under
    every flow, so search could not tell them apart and no page could say which codebases fire it.
    """
    return f"urn:li:dataJob:({rulebook_urn()},{rule.lower()})"


def rulebook_urn() -> str:
    """Return the flow every rule in the catalog belongs to, whichever repository ran it."""
    return flow_urn(_RULEBOOK)


def scope_urn(scope: str) -> str:
    """Return the identity one rule scope tag keeps across every run."""
    return f"urn:li:tag:{platform_key('scope', slug(scope))}"


def vocabulary_urn() -> str:
    """Return the identity of the group holding every word MCMR publishes a definition for."""
    return f"urn:li:glossaryNode:{platform_key('vocabulary')}"


def word_urn(word: str) -> str:
    """Return the identity one core vocabulary term keeps across every run."""
    return f"urn:li:glossaryTerm:{platform_key('word', slug(word))}"
