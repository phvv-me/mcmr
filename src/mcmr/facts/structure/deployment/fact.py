from pydantic import Field

from .groups import DeploymentFields


class DeploymentFact(DeploymentFields):
    """Describe a deployment path through its declared artifacts."""

    secrets_boundary: str = Field(
        default="", description="where deployment secrets are isolated at runtime"
    )
    rollback_command: str = Field(
        default="", description="command used to roll the deployment back"
    )
    provenance: str = Field(
        default="", description="identity of the attestation recording the deployment's provenance"
    )
