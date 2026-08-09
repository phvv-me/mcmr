from patos import FrozenModel
from pydantic import Field


class TypeAnnotationFields(FrozenModel):
    """Retain annotation path, union members, resolved names, and constraint recipe."""

    path: str = Field(description="repository relative path where the annotation is declared")
    union_members: list[str] = Field(
        default=[], description="resolved name of each member, when the annotation is a union"
    )
    resolved_names: list[str] = Field(
        default=[], description="resolved type names the annotation names"
    )
    constraint_recipe: str = Field(
        default="",
        description="verbatim Annotated expression the annotation reuses, empty when none",
    )
