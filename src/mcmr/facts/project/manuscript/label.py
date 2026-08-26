from pydantic import Field

from .place import ManuscriptPlace


class ManuscriptLabel(ManuscriptPlace):
    """Retain one cross reference target and what it names."""

    name: str = Field(default="", description="target name a reference would spell")
    kind: str = Field(
        default="",
        description="what the label names, such as a statement kind, a float kind, or a section",
    )
