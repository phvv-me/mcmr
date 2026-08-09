from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from collections.abc import MutableSequence


class Traversal(FrozenModel):
    """Return the strongly connected components of one directed graph.

    Tarjan's walk keeps five structures that only agree with each other between whole steps, and
    a caller who entered a node without descending from it, or settled one before its lowlink had
    propagated, would get a wrong answer rather than an error. So the structures are private, the
    steps that move them are private, and `components` is the only thing anybody can call. Each
    call starts the walk from nothing, which is what lets one graph be asked twice.
    """

    adjacency: Mapping[str, Sequence[str]]

    _indices: dict[str, int] = PrivateAttr(default_factory=dict)
    _lowlinks: dict[str, int] = PrivateAttr(default_factory=dict)
    _path: list[str] = PrivateAttr(default_factory=list)
    _active: set[str] = PrivateAttr(default_factory=set)
    _found: list[list[str]] = PrivateAttr(default_factory=list)

    def components(self) -> list[list[str]]:
        """Walk every disconnected region and return the completed components."""
        self._indices.clear()
        self._lowlinks.clear()
        self._path.clear()
        self._active.clear()
        self._found.clear()
        for start in sorted(self.adjacency):
            if start not in self._indices:
                self._walk(start)
        return self._found

    def _complete(self, node: str, pending: Sequence[tuple[str, int]]) -> None:
        """Complete one explored node and propagate its lowlink to its parent."""
        if self._lowlinks[node] == self._indices[node]:
            self._found.append(self._settle(node))
        if pending:
            holder = pending[-1][0]
            self._lowlinks[holder] = min(self._lowlinks[holder], self._lowlinks[node])

    def _descend(self, node: str, step: int, pending: MutableSequence[tuple[str, int]]) -> bool:
        """Schedule the first unseen neighbor or finish known neighbor updates."""
        for reached in range(step, len(self.adjacency[node])):
            target = self.adjacency[node][reached]
            if target not in self._indices:
                pending.extend(((node, reached + 1), (target, 0)))
                return True
            if target in self._active:
                self._lowlinks[node] = min(self._lowlinks[node], self._indices[target])
        return False

    def _enter(self, node: str) -> None:
        """Record a node when the traversal first reaches it."""
        self._indices[node] = self._lowlinks[node] = len(self._indices)
        self._path.append(node)
        self._active.add(node)

    def _settle(self, node: str) -> list[str]:
        """Take the nodes above one root off the walk as its completed component."""
        component: list[str] = []
        while True:
            member = self._path.pop()
            self._active.remove(member)
            component.append(member)
            if member == node:
                return component

    def _walk(self, start: str) -> None:
        """Complete an iterative depth-first walk from one unseen node."""
        pending: list[tuple[str, int]] = [(start, 0)]
        while pending:
            node, step = pending.pop()
            if step == 0:
                self._enter(node)
            if self._descend(node, step, pending):
                continue
            self._complete(node, pending)
