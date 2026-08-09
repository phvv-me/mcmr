from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from ....domain.primitives import NonEmptyStr


class KernelLaunchFact(Fact):
    """Describe one kernel launch and its execution configuration."""

    kernel: str = Field(default="", description="name of the launched kernel function")
    grid: NonEmptyStr = Field(description="grid dimension argument the launch states")
    block: NonEmptyStr = Field(description="block dimension argument the launch states")
    dynamic_shared_bytes: str = Field(
        default="",
        description="dynamic shared memory argument the launch states, empty when omitted",
    )
    stream: str = Field(
        default="", description="stream argument the launch states, empty for the default stream"
    )
    enclosing_function: str = Field(
        default="",
        description="name of the function the launch sits inside, empty when at file scope",
    )
    unit_uses_streams: bool = Field(
        default=False,
        description="whether the translation unit creates or is handed a CUDA stream anywhere",
    )
