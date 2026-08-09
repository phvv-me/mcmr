from typing import Literal

from patos import FrozenModel
from pydantic import Field, NonNegativeInt


class QueryOperationFields(FrozenModel):
    """Retain query kind, framework, transaction, shape, and selection count."""

    kind: Literal[
        "async_sessionmaker",
        "session_commit",
        "execute_scalars",
        "exec_scalars",
        "primary_key_first",
    ] = Field(description="which recognized database operation this record resolves to")
    framework: Literal["sqlalchemy", "sqlmodel"] = Field(
        description="ORM library the resolved operation is written against"
    )
    is_inside_loop: bool = Field(
        default=False, description="whether the operation executes inside a for or while loop"
    )
    expire_on_commit: bool = Field(
        default=True,
        description="whether the session factory leaves expire_on_commit at its default true",
    )
    has_unknown_keywords: bool = Field(
        default=False,
        description="whether the session factory call passes an unrecognized keyword",
    )
    selected_expression_count: NonNegativeInt = Field(
        default=0, description="expressions passed to the resolved select call"
    )
    has_primary_key_equality: bool = Field(
        default=False,
        description="whether the query filters the model's table by a primary key equality",
    )
