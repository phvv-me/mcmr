from typing import Literal

from patos import FrozenModel

from pydantic import Field, NonNegativeInt

from ...foundation import SourceSpan


class PydanticAnalysisFields:
    """Group flat Pydantic analysis fields by identity and construction."""

    class Field(FrozenModel):
        """Retain one model field annotation and its collection shape."""

        name: str = Field(description="name of the model field")
        annotation: str = Field(description="verbatim type annotation text of the model field")
        span: SourceSpan = Field(description="source range the field's annotation occupies")
        contains_variadic_tuple: bool = Field(
            default=False,
            description="whether the field's annotation contains a homogeneous variadic tuple",
        )

    class Validator(FrozenModel):
        """Retain structural evidence for one imported Pydantic validator."""

        kind: Literal["field", "model_after", "other"] = Field(
            description="which Pydantic validator decorator and mode the method carries"
        )
        fields_read: list[str] = Field(
            default=[], description="model field names the validator reads off its receiver"
        )
        has_self_call: bool = Field(
            default=False, description="whether the validator calls a method on its receiver"
        )
        has_nonfield_access: bool = Field(
            default=False,
            description="whether the validator reads a nonfield attribute off its receiver",
        )
        declarative_constraint_count: NonNegativeInt = Field(
            default=0,
            description="declarative checks the validator performs, like strip or a bound compare",
        )
        proves_disjoint_optional_variants: bool = Field(
            default=False,
            description="whether the validator proves mutually exclusive optional field variants",
        )
        variant_count: NonNegativeInt = Field(
            default=0,
            description="mutually exclusive optional field variants the validator proves",
        )

    class Identity(FrozenModel):
        """Retain fields, validators, model role, foundation, and class form."""

        name: str = Field(description="name of the analyzed class")
        fields: list[PydanticAnalysisFields.Field] = Field(
            default=[], description="fields the class declares"
        )
        validators: list[PydanticAnalysisFields.Validator] = Field(
            default=[], description="Pydantic validators the class declares"
        )
        is_pydantic_model: bool = Field(
            default=False,
            description="whether the class derives from a base naming itself a model",
        )
        uses_flexible_model: bool = Field(
            default=False, description="whether the class derives from FrozenFlexModel"
        )
        flexible_base_span: SourceSpan | None = Field(
            default=None,
            description="source range of the FrozenFlexModel base, when the class uses one",
        )
        is_undecorated_plain_class: bool = Field(
            default=False,
            description="whether the class has no decorator and no base or keyword arguments",
        )

    class Construction(Identity):
        """Retain constructor, storage, validation, and identity measurements."""

        synchronous_init_count: NonNegativeInt = Field(
            default=0, description="synchronous __init__ methods the class declares"
        )
        fixed_parameter_count: NonNegativeInt = Field(
            default=0, description="parameters the class's first __init__ takes beyond self"
        )
        stored_parameter_count: NonNegativeInt = Field(
            default=0,
            description="unchanged __init__ parameters the constructor stores onto self",
        )
        validation_count: NonNegativeInt = Field(
            default=0,
            description="raise or assert statements the constructor performs on its parameters",
        )
        default_count: NonNegativeInt = Field(
            default=0, description="constructor parameters that carry a default value"
        )
        has_only_data_identity_methods: bool = Field(
            default=False,
            description="whether every method beside __init__ is a data identity protocol method",
        )


PydanticFieldAnalysis = PydanticAnalysisFields.Field
PydanticValidator = PydanticAnalysisFields.Validator
