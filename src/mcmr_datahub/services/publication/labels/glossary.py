from typing import TYPE_CHECKING

from .identities import (
    families_urn,
    family_urn,
    vocabulary_urn,
    word_urn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from pydantic import JsonValue

    from mcmr.plugins import RuleJob, RunGraph

# What the group holding every rule family term is called.
_FAMILIES = "MCMR Rule Families"

# What the group holding the words MCMR uses about its own work is called.
_VOCABULARY = "MCMR Vocabulary"

# Whose stamp a published term association carries, since nobody attached it by hand.
_ACTOR = "urn:li:corpuser:datahub"

# The words a reader has to share with MCMR before any of the published graph reads as anything,
# each defined where the reader already is rather than in a document they would have to find.
_WORDS = {
    "fact table": (
        "One family of facts the kernel extracted from a repository, held as a dataset whose "
        "rows are exactly what every rule about that family reads."
    ),
    "deterministic rule": (
        "A rule computed from repository structure alone, so two runs over the same code reach "
        "the same answer."
    ),
    "contextual rule": (
        "A rule judged by a classification backend the caller configured, so its answer carries "
        "a model and a confidence rather than only a count."
    ),
    "external rule": (
        "A rule that reads current evidence from a system outside the repository, so its answer "
        "can change while the code stays exactly as it was."
    ),
    "verdict": (
        "What one rule concluded about one subject in one completed run, recorded so a later run "
        "lands on the same timeline instead of starting a new one."
    ),
    "finding": (
        "One place a failing rule named, carrying the file it points at and the sentence that "
        "says what is wrong there."
    ),
    "repair": (
        "The edit a failing rule offers for the finding it reported, which a run can leave "
        "unoffered, preview, apply, or refuse."
    ),
    "writeback": (
        "The step where a finished run records everything it concluded into the catalog, so the "
        "conclusion outlives the terminal it was printed in."
    ),
    "rulebook": (
        "Every rule MCMR enforces, held as one flow so a rule stays a single entity whichever "
        "codebase happens to run it."
    ),
    "run": (
        "One whole MCMR invocation, recorded under the flow of the repository it judged so a "
        "reader can ask what a single command did."
    ),
    "intermittent finding": (
        "A subject whose verdict keeps turning from failing to passing and back inside the "
        "recorded window, which is a different problem from one that simply stays failing."
    ),
}

# What every rule is tagged with beside its family and lanes, which is the finding it reports
# and the repair it may offer.
_RULE_WORDS = ("finding", "repair")

# What a fact table is called beside the term for the table itself.
_TABLE_WORDS = ("fact table", "verdict")

# What the flow of one repository is called, which is the run history a writeback leaves.
_FLOW_WORDS = ("writeback", "run")

# What the one flow holding every rule is called.
_RULEBOOK_WORDS = ("rulebook",)

# What a fact table currently reporting an on and off subject is called, beside its usual terms.
_FLAPPING = "intermittent finding"


def defined(*words: str) -> dict[str, JsonValue]:
    """State the core vocabulary terms one published entity is an instance of."""
    return described(word_urn(word) for word in words if word in _WORDS)


def described(urns: Iterable[str]) -> dict[str, JsonValue]:
    """State one entity's glossary terms, or nothing at all when it belongs to none."""
    terms: list[JsonValue] = [{"urn": urn} for urn in dict.fromkeys(urns)]
    if not terms:
        return {}
    stated: JsonValue = {"terms": terms, "auditStamp": {"time": 0, "actor": _ACTOR}}
    return {"glossaryTerms": {"value": stated}}


def families(graph: RunGraph) -> list[str]:
    """Return every rule family this run reached, which is the taxonomy it publishes."""
    return sorted({job.family for job in graph.jobs if job.family})


def families_node() -> dict[str, JsonValue]:
    """State the group every rule family term hangs under."""
    return _node(
        families_urn(),
        name=_FAMILIES,
        stated="The families MCMR groups its rules into, one term each.",
    )


def family_term(family: str) -> dict[str, JsonValue]:
    """State the glossary term one rule family is browsed by."""
    return {
        "urn": family_urn(family),
        "glossaryTermInfo": {
            "value": {
                "name": family,
                "definition": f"Rules MCMR groups under the {family} family.",
                "termSource": "INTERNAL",
                "parentNode": families_urn(),
            }
        },
    }


def flow_terms() -> dict[str, JsonValue]:
    """State what the flow of one repository is, which is where its runs are listed."""
    return defined(*_FLOW_WORDS)


def rulebook_terms() -> dict[str, JsonValue]:
    """State what the one flow holding every rule is."""
    return defined(*_RULEBOOK_WORDS)


def rule_terms(job: RuleJob) -> dict[str, JsonValue]:
    """State what one rule is, which is its family, its lanes, and what a rule produces."""
    lanes = [f"{lane} rule" for lane in job.lanes]
    urns = [family_urn(job.family)] if job.family else []
    words = [word for word in [*lanes, *_RULE_WORDS] if word in _WORDS]
    return described([*urns, *(word_urn(word) for word in words)])


def table_terms(*, flapping: bool = False) -> dict[str, JsonValue]:
    """State what one fact table is, and whether it currently reports an on and off subject."""
    return defined(*_TABLE_WORDS, *([_FLAPPING] if flapping else []))


def vocabulary_node() -> dict[str, JsonValue]:
    """State the group every word MCMR defines about its own work hangs under."""
    return _node(
        vocabulary_urn(),
        name=_VOCABULARY,
        stated="The words MCMR uses about its own work, defined where a reader meets them.",
    )


def vocabulary_terms() -> Sequence[dict[str, JsonValue]]:
    """State every core word, so a reader never has to guess what MCMR means by one."""
    return [
        {
            "urn": word_urn(word),
            "glossaryTermInfo": {
                "value": {
                    "name": word,
                    "definition": definition,
                    "termSource": "INTERNAL",
                    "parentNode": vocabulary_urn(),
                }
            },
        }
        for word, definition in _WORDS.items()
    ]


def _node(urn: str, *, name: str, stated: str) -> dict[str, JsonValue]:
    """State one glossary group, which is a name and the sentence that says what hangs under it."""
    return {"urn": urn, "glossaryNodeInfo": {"value": {"name": name, "definition": stated}}}
