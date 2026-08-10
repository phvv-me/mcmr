from hashlib import sha1
from typing import TYPE_CHECKING

from .keys import platform_key, slug

if TYPE_CHECKING:
    from mcmr.plugins import RunRecord

_ENVIRONMENT = "PROD"

# What a subject already owned by another system starts with, which is the one shape a verdict
# keeps anchoring on instead of moving to a fact table this run published.
_GOVERNED = "urn:li:"


def assertion_urn(record: RunRecord) -> str:
    """Return the assertion identity one rule and subject keep across every later run.

    The digest is taken over what the verdict is about rather than where it is stored, so a rule
    failing at two files inside one fact table keeps two timelines while a rule about a warehouse
    asset keeps the single one it always had.
    """
    digest = sha1(record.anchor.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"urn:li:assertion:{platform_key(record.rule.lower(), digest)}"


def codebase_urn(repository: str) -> str:
    """Return the identity of the domain one repository files its own graph under."""
    return f"urn:li:domain:{platform_key('codebase', slug(repository))}"


def contract_id(name: str) -> str:
    """Return the deterministic contract key one fact table keeps across every publication.

    DataHub mints a contract from this key, so a second run updates the contract the first one
    wrote rather than stacking a second contract beside it on the same dataset.
    """
    return platform_key(slug(name))


def dataset_urn(name: str) -> str:
    """Return the catalog identity of one published fact table."""
    return f"urn:li:dataset:({platform_urn()},{name},{_ENVIRONMENT})"


def domain_urn(name: str) -> str:
    """Return the stable identity one configured domain name always resolves to."""
    return f"urn:li:domain:{platform_key(slug(name))}"


def flow_urn(repository: str) -> str:
    """Return the catalog identity of one repository's policy run."""
    return f"urn:li:dataFlow:({platform_key()},{repository},{_ENVIRONMENT})"


def instance_urn(run: str) -> str:
    """Return the catalog identity of one recorded MCMR invocation.

    The identity is the run identity itself rather than a digest of it, so the string stamped on
    every verdict this run recorded is the same string that opens the run beside them.
    """
    return f"urn:li:dataProcessInstance:{run}"


def job_urn(repository: str, *, job: str) -> str:
    """Return the catalog identity of one step inside a repository's policy run."""
    return f"urn:li:dataJob:({flow_urn(repository)},{job})"


def owner_urn(owner: str) -> str:
    """Return the identity of whoever a run publishes under, named plainly or in full."""
    return owner if owner.startswith(_GOVERNED) else f"urn:li:corpuser:{owner}"


def platform_urn() -> str:
    """Return the identity of the platform a published schema declares itself under."""
    return f"urn:li:dataPlatform:{platform_key()}"


def subject_urn(subject: str) -> str:
    """Return where one verdict is stored, which is its own identity when it already has one."""
    return subject if subject.startswith(_GOVERNED) else dataset_urn(subject)
