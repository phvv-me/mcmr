from pydantic import Field

from .groups import LifetimeAnnotationFields


class LifetimeAnnotation(LifetimeAnnotationFields):
    """Retain one declaration and every position where it names a lifetime."""

    beyond: list[str] = Field(
        default=[],
        description="lifetimes the declaration's bounds, where clause, or body still require",
    )
    required_by_syntax: list[str] = Field(
        default=[],
        description="lifetimes stable Rust requires naming under an argument-position impl Trait",
    )
