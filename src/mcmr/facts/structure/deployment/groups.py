from pydantic import Field

from ...foundation import Fact


class DeploymentFields(Fact):
    """Retain applicability, inputs, build, environment, artifact, migration, and configuration."""

    is_applicable: bool = Field(
        default=True, description="whether this project has a deployment target to reproduce"
    )
    locked_inputs: list[str] = Field(
        default=[], description="lockfiles pinning the deployment's build inputs"
    )
    build_command: str = Field(
        default="", description="command used to build the deployment artifact"
    )
    environment: str = Field(default="", description="identity of the target runtime environment")
    artifact_identity: str = Field(
        default="", description="content-addressed identity of the built deployment artifact"
    )
    migrations: list[str] = Field(
        default=[], description="migration scripts applied during deployment"
    )
    configuration_sources: list[str] = Field(
        default=[], description="configuration files applied at deployment"
    )
