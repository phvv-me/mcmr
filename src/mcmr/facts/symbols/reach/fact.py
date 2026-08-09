from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .declaration import SymbolReach


class SymbolReachFact(Fact):
    """Describe how far references to one module's declarations spread."""

    is_test_module: bool = Field(
        default=False, description="whether this module's path is a test path"
    )
    declarations: list[SymbolReach] = Field(
        default=[], description="declarations in this module and how far their references reach"
    )
