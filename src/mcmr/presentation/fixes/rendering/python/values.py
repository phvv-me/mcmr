import ast
from collections import Counter
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .....facts.foundation import SourceSpan


class CarriedValues:
    """Name what one span of a parsed module supplies to the code that reads it."""

    def __init__(self, tree: ast.Module, region: SourceSpan) -> None:
        self.tree = tree
        self.region = region

    @cached_property
    def data_names(self) -> Counter[str]:
        """Count each name the span supplies as a value rather than as a route it reaches by."""
        routed = self._routed()
        return Counter(
            node.id
            for node in self._within()
            if isinstance(node, ast.Name) and id(node) not in routed
        )

    @cached_property
    def stated_names(self) -> Counter[str]:
        """Count each name the span states, in whichever position it states it."""
        return Counter(node.id for node in self._within() if isinstance(node, ast.Name))

    @cached_property
    def unpackings(self) -> Counter[str]:
        """Count each value the span spreads with `*` or `**` instead of naming a field."""
        return Counter(ast.unparse(operand) for operand in self._spread())

    def _annotations(self) -> Iterator[ast.expr]:
        """Yield every annotation and return type the module declares."""
        for node in ast.walk(self.tree):
            match node:
                case ast.AnnAssign(annotation=stated) | ast.arg(annotation=stated) if stated:
                    yield stated
                case ast.FunctionDef(returns=stated) | ast.AsyncFunctionDef(returns=stated) if (
                    stated
                ):
                    yield stated
                case _:
                    continue

    def _holds(self, node: ast.expr) -> bool:
        """Whether one parsed expression lies completely inside this span."""
        opens = (node.lineno, node.col_offset)
        closes = (node.end_lineno or node.lineno, node.end_col_offset or 0)
        return (self.region.start_line, self.region.start_column) <= opens and closes <= (
            self.region.end_line,
            self.region.end_column,
        )

    def _routed(self) -> set[int]:
        """Return each name node stating what the span calls, imports, or declares as a type."""
        # A repair reroutes those three, so `list(values)` becomes `[values]`, while what a call
        # consumes stays a value the replacement still has to carry.
        imported = {
            (alias.asname or alias.name).split(".", 1)[0]
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in node.names
        }
        performed = (
            node.func
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        )
        declared = (
            name
            for annotation in self._annotations()
            for name in ast.walk(annotation)
            if isinstance(name, ast.Name)
        )
        reached = (
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Name) and node.id in imported
        )
        return {id(node) for node in (*performed, *declared, *reached)}

    def _spread(self) -> Iterator[ast.expr]:
        """Yield the operand of every sequence, mapping, and keyword unpacking in the span."""
        for node in self._within():
            match node:
                case ast.Starred(value=operand):
                    yield operand
                case ast.Dict(keys=keys, values=values):
                    yield from (
                        value for key, value in zip(keys, values, strict=True) if key is None
                    )
                case ast.Call(keywords=keywords):
                    yield from (item.value for item in keywords if item.arg is None)
                case _:
                    continue

    def _within(self) -> Iterator[ast.expr]:
        """Yield every expression the span completely contains."""
        return (
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.expr) and self._holds(node)
        )
