import re
from base64 import b64encode
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import JsonValue

# The data platform every fact table, flow, and rule job MCMR publishes is attributed to.
_PLATFORM = "mcmr"

# The environment DataHub keys a dataset and a flow by, which one repository has exactly one of.
_ENVIRONMENT = "PROD"

# What a subject already owned by another system starts with, which is the one shape a verdict
# keeps anchoring on instead of moving to a fact table this run published.
_GOVERNED = "urn:li:"

# The one flow every rule belongs to, which is what makes a rule a single global entity.
_RULEBOOK = "rulebook"

# The mark shown on the platform card, which travels inside the aspect as an ordinary image
# source rather than as an asset served from anywhere.
_LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0F172A"/>'
    '<g fill="none" stroke="#38BDF8" stroke-width="5" stroke-linecap="round">'
    '<path d="M25 17c-6 0-7 3-7 7v4c0 3-2 4-4 4 2 0 4 1 4 4v4c0 4 1 7 7 7"/>'
    '<path d="M39 17c6 0 7 3 7 7v4c0 3 2 4 4 4-2 0-4 1-4 4v4c0 4-1 7-7 7"/></g>'
    '<path d="M25 33l5 6 9-13" fill="none" stroke="#4ADE80" stroke-width="6" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def dataset_urn(name: str) -> str:
    """Return the catalog identity of one published fact table."""
    return f"urn:li:dataset:(urn:li:dataPlatform:{_PLATFORM},{name},{_ENVIRONMENT})"


def domain_entity(name: str) -> dict[str, JsonValue]:
    """Return the domain every repository MCMR publishes is filed under."""
    return {
        "urn": domain_urn(name),
        "domainProperties": {
            "value": {
                "name": name,
                "description": "Repositories MCMR publishes as fact tables and rule jobs.",
            }
        },
    }


def domain_urn(name: str) -> str:
    """Return the stable identity one configured domain name always resolves to."""
    return f"urn:li:domain:{_PLATFORM}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"


def flow_urn(repository: str) -> str:
    """Return the catalog identity of one repository's policy run."""
    return f"urn:li:dataFlow:({_PLATFORM},{repository},{_ENVIRONMENT})"


def job_urn(repository: str, *, job: str) -> str:
    """Return the catalog identity of one step inside a repository's policy run."""
    return f"urn:li:dataJob:({flow_urn(repository)},{job})"


def owner_urn(owner: str) -> str:
    """Return the identity of whoever a run publishes under, named plainly or in full."""
    return owner if owner.startswith(_GOVERNED) else f"urn:li:corpuser:{owner}"


def platform_entity() -> dict[str, JsonValue]:
    """Return the platform every entity MCMR publishes is attributed to."""
    logo = b64encode(_LOGO.encode("utf-8")).decode("ascii")
    return {
        "urn": platform_urn(),
        "dataPlatformInfo": {
            "value": {
                "name": _PLATFORM,
                "displayName": "MCMR",
                "type": "OTHERS",
                "datasetNameDelimiter": "/",
                "logoUrl": f"data:image/svg+xml;base64,{logo}",
            }
        },
    }


def platform_urn() -> str:
    """Return the identity of the platform a published schema declares itself under."""
    return f"urn:li:dataPlatform:{_PLATFORM}"


def post_urn(repository: str) -> str:
    """Return the home page card one repository keeps across every run that announces it."""
    return f"urn:li:post:{_PLATFORM}-{repository}"


def rule_urn(rule: str) -> str:
    """Return the one identity a rule keeps for the whole instance, whatever runs it.

    A rule is one thing. Publishing it per repository would put a copy of `ALL-DUPL0005` under
    every flow, so search could not tell them apart and no page could say which codebases fire it.
    """
    return f"urn:li:dataJob:({rulebook_urn()},{rule.lower()})"


def rulebook_urn() -> str:
    """Return the flow every rule in the catalog belongs to, whichever repository ran it."""
    return flow_urn(_RULEBOOK)


def subject_urn(subject: str) -> str:
    """Return where one verdict is stored, which is its own identity when it already has one."""
    return subject if subject.startswith(_GOVERNED) else dataset_urn(subject)
