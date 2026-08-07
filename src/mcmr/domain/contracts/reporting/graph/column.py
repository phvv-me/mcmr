from patos import FrozenModel

from ....primitives import NonEmptyStr
from .kind import ColumnType


class FactColumn(FrozenModel):
    """State one leaf of a fact model as the dotted column a catalog schema shows."""

    path: NonEmptyStr
    data_type: ColumnType = ColumnType.STRING
    native: str = ""
    description: str = ""
