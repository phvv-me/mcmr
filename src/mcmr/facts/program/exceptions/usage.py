from patos import FrozenModel
from pydantic import Field


class ExceptionUsage(FrozenModel):
    """Retain one project exception and its ordinary importing modules."""

    name: str = Field(description="name of the declared exception class")
    defining_module: str = Field(description="dotted module where the exception class is declared")
    importing_modules: list[str] = Field(
        default=[], description="ordinary modules that import the exception class by name"
    )
