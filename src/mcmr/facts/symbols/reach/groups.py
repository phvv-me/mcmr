from typing import TYPE_CHECKING, Literal

from patos import FrozenModel
from pydantic import Field

from ...foundation import SourceSpan, Visibility

if TYPE_CHECKING:
    from pydantic import NonNegativeInt


class SymbolReachFields:
    """Group flat reach fields by declaration, spread, and operation."""

    class Identity(FrozenModel):
        """Retain declaration identity and stated visibility."""

        qualname: str = Field(description="fully qualified name of this declaration")
        kind: Literal["class", "function", "method", "property", "variable", "attribute"] = Field(
            description="language-neutral kind of this declaration"
        )
        span: SourceSpan = Field(description="source location of this declaration")
        visibility: Visibility = Field(
            default=Visibility.PUBLIC, description="effective visibility of this declaration"
        )

    class Declaration(Identity):
        """Retain owner contract, scope, and local references."""

        owner_visibility: Visibility = Field(
            default=Visibility.PUBLIC,
            description="visibility of the class or module that owns this declaration",
        )
        owner_has_inheritance: bool = Field(
            default=False,
            description="whether the owner participates in an inheritance edge, base or subclass",
        )
        is_module_scope: bool = Field(
            default=False,
            description="whether this declaration sits directly in its module's scope",
        )
        is_decorated: bool = Field(
            default=False,
            description="whether this declaration carries a decorator or a registered component",
        )
        own_file_references: NonNegativeInt = Field(
            default=0, description="references reaching this declaration from its own file"
        )

    class Ownership(Declaration):
        """Retain cross-file and owner resolution completeness."""

        other_file_references: NonNegativeInt = Field(
            default=0, description="references reaching this declaration from a different file"
        )
        owner_references: NonNegativeInt = Field(
            default=0, description="references reaching this declaration from within its own owner"
        )
        non_owner_references: NonNegativeInt = Field(
            default=0, description="references reaching this declaration from outside its owner"
        )
        unresolved_name_references: NonNegativeInt = Field(
            default=0,
            description="edges reaching an unresolved symbol sharing this declaration's trailing "
            "name",
        )

    class Spread(Ownership):
        """Retain repository spread and resolved operation counts."""

        referencing_files: NonNegativeInt = Field(
            default=0, description="distinct files that reference this declaration"
        )
        referencing_directories: NonNegativeInt = Field(
            default=0, description="distinct directories that reference this declaration"
        )
        referencing_packages: NonNegativeInt = Field(
            default=0, description="distinct packages that reference this declaration"
        )
        call_count: NonNegativeInt = Field(
            default=0, description="call edges reaching this declaration"
        )
        instantiate_count: NonNegativeInt = Field(
            default=0, description="instantiate edges reaching this declaration"
        )
        inherit_count: NonNegativeInt = Field(
            default=0, description="inherit edges reaching this declaration"
        )

    class Operations(Spread):
        """Retain import operations reaching the declaration."""

        import_count: NonNegativeInt = Field(
            default=0, description="import edges reaching this declaration"
        )
