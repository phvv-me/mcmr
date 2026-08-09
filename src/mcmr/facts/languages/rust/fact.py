from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .clone import CloneCall
    from .lifetimes import LifetimeAnnotation, StaticLifetime


class RustSurfaceFact(Fact):
    """Describe the borrowing, pinning, and copying surface of one Rust module."""

    annotations: list[LifetimeAnnotation] = Field(
        default=[], description="lifetime annotations this module's declarations state"
    )
    pins: list[StaticLifetime] = Field(
        default=[], description="'static lifetimes this module states"
    )
    clones: list[CloneCall] = Field(default=[], description="explicit copies this module makes")
