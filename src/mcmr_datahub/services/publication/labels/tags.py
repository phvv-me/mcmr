from typing import TYPE_CHECKING

from .identities import category_urn, lane_urn, scope_urn

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pydantic import JsonValue

    from mcmr.plugins import FactDataset, RuleJob, RunGraph

# What each execution lane means, said where a reader filtering by it can read it.
_LANES = {
    "deterministic": "Computed from repository structure, so it answers the same way twice.",
    "contextual": "Estimated by a classification backend the caller configured.",
    "external": "Reads current evidence from a system outside the repository.",
}

# What each lane looks like in a list, so a scan separates them without reading.
_LANE_COLOURS = {"deterministic": "#38BDF8", "contextual": "#A78BFA", "external": "#FBBF24"}

# What each group of fact tables holds, taken from the directory the fact models already live in
# so the taxonomy on screen is the taxonomy in the source rather than a second one to maintain.
_CATEGORIES = {
    "structure": "How a repository is arranged, from directories and classes to calls and CI.",
    "program": "What the program does, from modules and functions to exceptions and lineage.",
    "project": "The project around the code, from configuration and history to prose and risk.",
    "symbols": "The names a codebase declares, exports, overrides, reaches, and types.",
    "testing": "The test suite, from cases and fixtures to waivers and quarantined tests.",
    "languages": "What one language contributes that no other language has to answer for.",
    "foundation": "What every other family is built out of, such as spans, evidence, and graphs.",
}

# What each group of fact tables looks like in a list.
_CATEGORY_COLOURS = {
    "structure": "#34D399",
    "program": "#60A5FA",
    "project": "#F472B6",
    "symbols": "#C084FC",
    "testing": "#FCD34D",
    "languages": "#FB923C",
    "foundation": "#94A3B8",
}

# What each rule identifier prefix answers for, which is the one thing a scope tag states.
_SCOPES = {
    "all": "Answers for every language a repository is written in.",
    "py": "Answers only for Python source.",
    "rs": "Answers only for Rust source.",
    "ts": "Answers only for TypeScript source.",
    "c": "Answers only for C source.",
    "cpp": "Answers only for C++ source.",
    "cu": "Answers only for CUDA source.",
}

# What each rule scope looks like in a list.
_SCOPE_COLOURS = {
    "all": "#64748B",
    "py": "#3776AB",
    "rs": "#DEA584",
    "ts": "#3178C6",
    "c": "#A8B9CC",
    "cpp": "#00599C",
    "cu": "#76B900",
}

# What separates a rule identifier's scope from the family and number that follow it.
_PREFIX = "-"


def categories(graph: RunGraph) -> list[str]:
    """Return every fact group this run materialized, so an unused tag is never created."""
    return sorted(
        {dataset.category for dataset in graph.datasets if dataset.category in _CATEGORIES}
    )


def category_entity(category: str) -> dict[str, JsonValue]:
    """State the tag one group of fact tables is filtered by."""
    return _tag(
        category_urn(category),
        name=f"facts {category}",
        description=_CATEGORIES[category],
        colour=_CATEGORY_COLOURS[category],
    )


def lane_entity(lane: str) -> dict[str, JsonValue]:
    """State the tag one lane is filtered by, colored so a list reads at a glance."""
    return _tag(
        lane_urn(lane),
        name=lane,
        description=_LANES[lane],
        colour=_LANE_COLOURS[lane],
    )


def lanes(graph: RunGraph) -> list[str]:
    """Return every execution lane this run reached, so an unused tag is never created."""
    return sorted({lane for job in graph.jobs for lane in job.lanes if lane in _LANES})


def _rule_scope(job: RuleJob) -> str:
    """Return the language one rule answers for, which its own identifier already states."""
    prefix = job.rule.split(_PREFIX, 1)[0].lower()
    return prefix if prefix in _SCOPES else ""


def scope_entity(scope: str) -> dict[str, JsonValue]:
    """State the tag one rule scope is filtered by."""
    return _tag(
        scope_urn(scope),
        name=f"scope {scope}",
        description=_SCOPES[scope],
        colour=_SCOPE_COLOURS[scope],
    )


def scopes(graph: RunGraph) -> list[str]:
    """Return every language scope this run's rules answered for."""
    return sorted({found for job in graph.jobs if (found := _rule_scope(job))})


def _tagged(urns: Iterable[str]) -> dict[str, JsonValue]:
    """State one entity's tags, or nothing at all when it carries none."""
    tags: list[JsonValue] = [{"tag": urn} for urn in dict.fromkeys(urns)]
    return {"globalTags": {"value": {"tags": tags}}} if tags else {}


def rule_tags(job: RuleJob) -> dict[str, JsonValue]:
    """State the lanes one rule answers in and the language it answers for.

    A lane is what a reader filters a rulebook of hundreds by, and a rule needing both a model
    and a network carries both tags rather than losing one to the single type label.
    """
    lanes = [lane_urn(lane) for lane in job.lanes if lane in _LANES]
    scope = [scope_urn(found)] if (found := _rule_scope(job)) else []
    return _tagged([*lanes, *scope])


def table_tags(dataset: FactDataset) -> dict[str, JsonValue]:
    """State the group one fact table belongs to, which is where its facts are defined."""
    return _tagged([category_urn(dataset.category)] if dataset.category in _CATEGORIES else [])


def _tag(urn: str, *, name: str, description: str, colour: str) -> dict[str, JsonValue]:
    """State one tag with the color and sentence that make a filter list readable."""
    return {
        "urn": urn,
        "tagProperties": {"value": {"name": name, "description": description, "colorHex": colour}},
    }
