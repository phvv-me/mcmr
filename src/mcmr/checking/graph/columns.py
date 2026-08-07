from enum import EnumType
from functools import cache
from types import UnionType
from typing import TYPE_CHECKING, Annotated, TypeAliasType, get_args, get_origin

from patos import FrozenModel

from ...domain.contracts import ColumnType, FactColumn

if TYPE_CHECKING:
    from collections.abc import Sequence

# What each leaf stores, checked before the numeric widening a `bool` would otherwise reach.
_SCALARS = ((bool, ColumnType.BOOLEAN), (int, ColumnType.NUMBER), (float, ColumnType.NUMBER))

# The annotation forms whose first argument is the value a field really stores, which covers an
# alias, an optional, and every sequence a fact model declares.
_FIRST = {Annotated, UnionType, list, set, frozenset, tuple}


@cache
def fact_columns(family: type[FrozenModel]) -> list[FactColumn]:
    """Flatten one fact model into the dotted columns a catalog schema states.

    A fact model nests records inside records, which is exactly what a DataHub schema spells as a
    dotted field path, so the projection walks the declared model rather than the relations the
    kernel happened to build. A model reachable from itself, which `Expression` is, stops the walk
    at the first repeat instead of describing an infinite schema.
    """
    return _walk(family, prefix="", enclosing=[])


def _element(annotation: type | TypeAliasType) -> type:
    """Return the value one field stores, without its aliases, optionality, or container."""
    while not isinstance(annotation, type):
        if isinstance(annotation, TypeAliasType):
            annotation = annotation.__value__
            continue
        arguments = [item for item in get_args(annotation) if item is not type(None)]
        origin = get_origin(annotation)
        if not arguments or origin not in _FIRST | {dict}:
            return str
        annotation = arguments[-1] if origin is dict else arguments[0]
    return annotation


def _scalar(annotation: type) -> ColumnType:
    """Return the value domain one leaf annotation stores."""
    if isinstance(annotation, EnumType):
        return ColumnType.STRING
    return next(
        (column for stored, column in _SCALARS if annotation is stored),
        ColumnType.STRING,
    )


def _walk(
    model: type[FrozenModel],
    *,
    prefix: str,
    enclosing: Sequence[type[FrozenModel]],
) -> list[FactColumn]:
    """Return every leaf below one model, named by the dotted path that reaches it."""
    columns: list[FactColumn] = []
    for name, field in model.model_fields.items():
        annotation = _element(field.annotation or str)
        path = f"{prefix}{name}"
        nested = issubclass(annotation, FrozenModel) and annotation not in enclosing
        if nested:
            deeper = [*enclosing, model, annotation]
            columns.extend(_walk(annotation, prefix=f"{path}.", enclosing=deeper))
            continue
        columns.append(
            FactColumn(
                path=path,
                data_type=_scalar(annotation),
                native=annotation.__name__,
                description=field.description or "",
            )
        )
    return columns
