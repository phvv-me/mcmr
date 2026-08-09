from typing import TYPE_CHECKING, Literal

from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ...foundation import Fact, SourceSpan, Visibility

if TYPE_CHECKING:
    from .method import MethodAnalysis


class ClassFact(Fact):
    """Describe one class and its resolved members."""

    class AnalysisIdentity(FrozenModel):
        """Retain class identity, source, scope, and visibility."""

        name: str = Field(description="name the class declares")
        path: str = Field(description="repository relative path where the class is declared")
        span: SourceSpan = Field(description="source range the class declaration occupies")
        is_test: bool = Field(
            default=False, description="whether the class is declared in a test module"
        )
        source: str = Field(
            default="", description="verbatim source text of the class declaration"
        )
        scope: Literal["module", "nested"] = Field(
            default="module",
            description="whether the class is declared at module level or nested in another scope",
        )
        visibility: Visibility = Field(
            default=Visibility.PUBLIC,
            description="how widely the class name is exposed, derived from its naming convention",
        )

    class AnalysisDeclaration(AnalysisIdentity):
        """Retain bases, protocol, decoration, method, and state declarations."""

        direct_bases: list[str] = Field(
            default=[], description="literal source text of each base class the class states"
        )
        is_protocol: bool = Field(
            default=False, description="whether the class derives typing.Protocol"
        )
        decorators: list[str] = Field(
            default=[], description="literal source text of each decorator applied to the class"
        )
        class_keywords: list[str] = Field(
            default=[],
            description="literal source text of each keyword argument in the class definition",
        )
        methods: list[MethodAnalysis] = Field(default=[], description="methods the class declares")
        has_explicit_registry_name: bool = Field(
            default=False,
            description="whether the class overrides its derivable registry key with an "
            "explicit name",
        )
        has_instance_fields: bool = Field(
            default=False, description="whether the class declares any instance field of its own"
        )

    class AnalysisReach(AnalysisDeclaration):
        """Retain fields, inheritance reach, instantiation, and export evidence."""

        field_count: NonNegativeInt = Field(
            default=0, description="number of instance fields the class declares directly"
        )
        has_inherited_fields: bool = Field(
            default=False,
            description="whether a resolved ancestor already declares instance fields",
        )
        direct_subclasses: list[str] = Field(
            default=[], description="names of classes that directly derive this class"
        )
        descendant_count: NonNegativeInt = Field(
            default=0, description="number of classes transitively deriving this class"
        )
        is_instantiated: bool = Field(
            default=False,
            description="whether the class is constructed anywhere in the resolved sources",
        )
        is_exported: bool = Field(
            default=False, description="whether the class name is exported from its module"
        )
        only_cross_module_reference_is_subclass: bool = Field(
            default=False,
            description="whether every cross module reference to this class is its one direct "
            "subclass declaration",
        )

    class AnalysisComposition(AnalysisReach):
        """Retain layering, base overlap, collisions, and model role evidence."""

        is_pass_through_layer: bool = Field(
            default=False,
            description="whether the class body only passes or forwards every method unchanged "
            "to super",
        )
        base_is_removable_overlap: bool = Field(
            default=False,
            description="whether the class's own base is already reported as a removable single "
            "subclass base",
        )
        has_redundant_direct_base: bool = Field(
            default=False,
            description="whether one direct base already inherits another direct base of this "
            "class",
        )
        has_noncooperative_concrete_collision: bool = Field(
            default=False,
            description="whether multiple direct bases provide the same concrete method without "
            "cooperative super delegation",
        )
        duplicate_component_alias_count: NonNegativeInt = Field(
            default=0,
            description="number of fields assigned directly from an attribute of a component the "
            "class already retains",
        )
        is_declarative_model: bool = Field(
            default=False,
            description="whether the class is a recognized declarative model such as a Pydantic "
            "model, SQL table, or dataclass",
        )
        is_dataclass: bool = Field(
            default=False, description="whether the class is decorated as a dataclass"
        )

    class AnalysisModel(AnalysisComposition):
        """Retain behavior, imports, destinations, and Pydantic foundation evidence."""

        has_ordinary_behavior: bool = Field(
            default=False,
            description="whether the class declares a method beyond protocol stubs and Pydantic "
            "validation or serialization hooks",
        )
        states_model_configuration: bool = Field(
            default=False,
            description="whether the class declares a nested Config class or binds model_config",
        )
        importing_modules: list[str] = Field(
            default=[], description="modules outside this class's own that import it"
        )
        proposed_model_destination: str = Field(
            default="",
            description="shared models file path proposed when several modules import this class, "
            "empty when none is proposed",
        )
        directly_inherits_pydantic_base_model: bool = Field(
            default=False, description="whether the class derives pydantic.BaseModel directly"
        )
        inherits_approved_model_foundation: bool = Field(
            default=False,
            description="whether a direct base resolves to the project's approved model "
            "foundation",
        )

    class Analysis(AnalysisModel):
        """Retain one class and its closed-world graph properties."""

    class CoupledTypeGroup(FrozenModel):
        """Retain short co-imported role types sharing a name prefix."""

        prefix: str = Field(description="shared camel case name prefix grouping these classes")
        span: SourceSpan = Field(description="source range of the first class in the group")
        role_suffixes: list[str] = Field(
            default=[], description="distinct name suffixes following the shared prefix"
        )
        type_count: NonNegativeInt = Field(description="number of classes sharing the prefix")
        maximum_type_lines: NonNegativeInt = Field(
            description="largest line count among the grouped classes"
        )
        coimporting_module_count: NonNegativeInt = Field(
            description="number of modules importing at least two of these types together"
        )

    class ModelFile(FrozenModel):
        """Retain one implementation file below a shared models directory."""

        path: str = Field(description="repository relative path of the file")
        span: SourceSpan = Field(description="source range of the file's module")
        top_level_class_count: NonNegativeInt = Field(
            description="number of top level classes the file declares"
        )
        model_class_count: NonNegativeInt = Field(
            description="number of those classes that are declarative models"
        )
        is_package_initializer: bool = Field(
            default=False, description="whether the file is a package __init__.py"
        )

    class AttributeProjection(FrozenModel):
        """Retain matching key and attribute projections from one typed root."""

        root: str = Field(description="local name whose attributes the literal reads")
        span: SourceSpan = Field(description="source range of the dict or call literal")
        attribute_names: list[str] = Field(
            default=[], description="attribute names read off the root, in encountered order"
        )
        output_keys: list[str] = Field(
            default=[],
            description="literal keys or keyword names the literal assigns each attribute to",
        )

    classes: list[Analysis] = Field(default=[], description="classes this file declares")
    coupled_groups: list[CoupledTypeGroup] = Field(
        default=[], description="co-imported role type groups detected for this file"
    )
    model_files: list[ModelFile] = Field(
        default=[], description="this file's entry when it sits inside a shared models package"
    )
    projection_groups: list[AttributeProjection] = Field(
        default=[], description="attribute projection groups detected in this file"
    )
    has_approved_model_foundation_policy: bool = Field(
        default=False,
        description="whether the repository states an approved model foundation policy",
    )
