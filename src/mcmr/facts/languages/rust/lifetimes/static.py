from typing import Literal

from patos import FrozenModel
from pydantic import Field, PositiveInt


class StaticLifetime(FrozenModel):
    """Retain one position that pins something for the whole program run."""

    owner: str = Field(
        default="",
        description="function, method, or field the 'static lifetime belongs to, empty at module "
        "level",
    )
    line: PositiveInt = Field(default=1, description="line the 'static lifetime is written on")
    position: Literal["demand", "supply", "bound"] = Field(
        default="supply",
        description="whether the pin is demanded of a caller, supplied to one, or a generic bound",
    )
