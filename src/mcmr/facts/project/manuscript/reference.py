from pydantic import Field

from .place import ManuscriptPlace


class ManuscriptReference(ManuscriptPlace):
    """Retain one cross reference and how it was spelled."""

    target: str = Field(default="", description="label name this reference points at")
    command: str = Field(default="", description="command that spelled the reference")
