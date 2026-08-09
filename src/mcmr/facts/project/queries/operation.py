from typing import TYPE_CHECKING

from pydantic import Field

from .groups import QueryOperationFields

if TYPE_CHECKING:
    from ...foundation import NodeRef


class QueryOperation(QueryOperationFields):
    """Retain one resolved SQLAlchemy or SQLModel operation chain."""

    has_execution_options: bool = Field(
        default=False, description="whether the query chain calls execution_options"
    )
    node: NodeRef = Field(description="syntax node the resolved operation's call occupies")
    scalars_segment: NodeRef | None = Field(
        default=None, description="editable span of the trailing scalars call, when present"
    )
    execute_segment: NodeRef | None = Field(
        default=None, description="editable span of the exec or execute method name, when present"
    )
