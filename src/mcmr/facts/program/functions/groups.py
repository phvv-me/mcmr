from typing import TYPE_CHECKING, Literal

from pydantic import Field

from ...foundation import Fact, NodeRef, Visibility

if TYPE_CHECKING:
    from pydantic import NonNegativeInt

    from .types import FunctionTypes


class FunctionFields:
    """Group contiguous function fields without changing their wire order."""

    class Execution(Fact):
        """Retain task, receiver, cache, and documentation evidence."""

        created_task_count: NonNegativeInt = Field(
            default=0, description="asyncio task creator calls the executable body makes"
        )
        is_test: bool = Field(
            default=False, description="whether the function is declared in a test module"
        )
        gather_consumes_created_tasks: bool = Field(
            default=False,
            description="whether a gather call in the body waits on tasks the body itself created",
        )
        gather_returns_exceptions: bool = Field(
            default=False,
            description="whether a gather call in the body passes return_exceptions as true",
        )
        has_task_group: bool = Field(
            default=False, description="whether the body opens an asyncio task group"
        )
        reads_receiver: bool = Field(
            default=False,
            description="whether the body reads the instance or class receiver it was handed",
        )
        cache_decorator: Literal["", "cached_property", "cache", "lru_cache"] = Field(
            default="",
            description="decorator that caches this callable's result, empty when none applies",
        )

    class Identity(Execution):
        """Retain documentation, tensor semantics, and callable identity."""

        docstring: str = Field(
            default="", description="docstring text the function declares, empty when absent"
        )
        recognized_tensor_roles: list[str] = Field(
            default=[],
            description="tensor roles the function's parameter and return annotations name",
        )
        has_tensor_shape_semantics: bool = Field(
            default=False, description="whether an annotation states a tensor's shape"
        )
        has_tensor_dtype_semantics: bool = Field(
            default=False, description="whether an annotation states a tensor's dtype"
        )
        name: str = Field(default="", description="name the function is declared with")
        scope: Literal["module", "method", "nested"] = Field(
            default="module",
            description="where the function is declared, at module level, as a method, or nested",
        )
        visibility: Visibility = Field(
            default=Visibility.PUBLIC,
            description="visibility the function's name implies in its scope",
        )

    class Address(Identity):
        """Retain protocol identity and exact source nodes."""

        is_protocol_name: bool = Field(
            default=False, description="whether the function's name is a dunder spelling"
        )
        definition: NodeRef | None = Field(
            default=None, description="syntax node of the function's own definition"
        )
        body_expression: NodeRef | None = Field(
            default=None,
            description="syntax node of the body's sole expression, when the body is exactly one",
        )
        references: list[NodeRef] = Field(
            default=[], description="syntax nodes of the call sites this function is invoked from"
        )

    class Source(Address):
        """Retain sole ownership evidence and direct source measures."""

        sole_reference_owner_definition: NodeRef | None = Field(
            default=None,
            description="syntax node of the sole method definition that calls this function",
        )
        implementation_lines: NonNegativeInt = Field(
            default=0,
            description="physical source lines the executable body occupies, code only",
        )
        direct_statement_count: NonNegativeInt = Field(
            default=0, description="top-level statements the executable body holds"
        )
        reference_count: NonNegativeInt = Field(
            default=0, description="times the function's name is loaded in its declaring module"
        )

    class Structure(Source):
        """Retain behavior, controls, parameters, decorators, and recursion."""

        behavior_operation_count: NonNegativeInt = Field(
            default=0, description="expressions in the body that perform behavior, not pure access"
        )
        conditional_count: NonNegativeInt = Field(
            default=0, description="conditional control structures in the body"
        )
        control_increments: list[FunctionTypes.ControlIncrement] = Field(
            default=[], description="control structures in the body and their nesting depth"
        )
        parameters: list[FunctionTypes.Parameter] = Field(
            default=[], description="parameters this function declares"
        )
        decorators: list[str] = Field(
            default=[], description="decorator expressions applied to this function"
        )
        sole_reference_owner_class: str = Field(
            default="", description="class of the sole method that calls this function"
        )
        is_async: bool = Field(default=False, description="whether the function is declared async")

    class Contract(Structure):
        """Retain recursion, reference, and callable contract evidence."""

        is_recursive: bool = Field(
            default=False, description="whether the body calls the function by its own name"
        )
        is_first_class_reference: bool = Field(
            default=False,
            description="whether the function's name is loaded somewhere other than a direct call",
        )
        is_abstract: bool = Field(
            default=False,
            description="whether the function wears an abstractmethod or abstractproperty",
        )
        is_protocol_member: bool = Field(
            default=False,
            description="whether the function's owning class directly bases Protocol",
        )
        is_overload: bool = Field(
            default=False, description="whether the function wears an overload decorator"
        )
        is_property: bool = Field(
            default=False,
            description="whether the function wears a property or accessor decorator",
        )
        is_framework_hook: bool = Field(
            default=False,
            description="whether something other than this project decides when the function runs",
        )

    class Body(Contract):
        """Retain framework, polymorphism, and compact-body evidence."""

        is_declarative_body: bool = Field(
            default=False,
            description="whether the function wears a rule decorator or its body is control-free "
            "and returns a query plan",
        )
        is_polymorphic: bool = Field(
            default=False, description="whether the function wears an override decorator"
        )
        is_pass_body: bool = Field(
            default=False, description="whether the executable body is exactly one pass statement"
        )
        is_raise_body: bool = Field(
            default=False, description="whether the executable body is exactly one raise statement"
        )
        returns_single_call: bool = Field(
            default=False,
            description="whether the executable body is exactly one return of a call expression",
        )
        forwards_only_parameter_unchanged: bool = Field(
            default=False,
            description="whether the function takes one required parameter and returns it "
            "unchanged from one call",
        )
        is_model_method: bool = Field(
            default=False,
            description="whether the function's owning class bases a model foundation",
        )

    class Validation(Body):
        """Retain Pydantic and validation behavior."""

        is_pydantic_validator: bool = Field(
            default=False, description="whether the function wears a pydantic validator decorator"
        )
        checks_raw_input_type: bool = Field(
            default=False,
            description="whether the body calls isinstance or issubclass on one of its parameters",
        )
        raises_validation_exception: bool = Field(
            default=False,
            description="whether the body raises an exception from the validation vocabulary",
        )
        constructs_owner_model: bool = Field(
            default=False,
            description="whether the body constructs an instance of the class that declares it",
        )
