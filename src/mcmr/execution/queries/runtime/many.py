import asyncio
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from enum import StrEnum

    from ..model import ModelQuery
    from .backend import ClassificationBackend
    from .resolved import ResolvedQuery


@runtime_checkable
class ManyQueryBackend(Protocol):
    """Expose native execution across independent contextual rule queries."""

    async def answered_many(
        self,
        queries: Sequence[ModelQuery[StrEnum]],
    ) -> Sequence[ResolvedQuery]:
        """Answer independent contextual rules through one backend strategy."""
        ...


async def answer_many(
    backend: ClassificationBackend,
    queries: Sequence[ModelQuery[StrEnum]],
) -> Sequence[ResolvedQuery]:
    """Use a backend's repository strategy or execute its independent query strategy."""
    if isinstance(backend, ManyQueryBackend):
        return await backend.answered_many(queries)
    return await asyncio.gather(*(backend.answered(query) for query in queries))
