from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact, NodeRef

if TYPE_CHECKING:
    from pydantic import NonNegativeInt


class ImportBindingFields:
    """Group flat import fields by identity, role, and visibility."""

    class Identity(Fact):
        """Retain imported and bound names."""

        name: str = Field(description="local name the import binds")
        module: str = Field(description="dotted module the import statement names")
        imported_name: str = Field(
            default="", description="exact name imported from the module before any aliasing"
        )
        importer_module: str = Field(
            default="", description="dotted module name of the file containing the import"
        )

    class Source(Identity):
        """Retain exact source nodes and the number of qualifying reads."""

        declaration: NodeRef | None = Field(
            default=None, description="syntax node the whole import statement occupies"
        )
        binding: NodeRef | None = Field(
            default=None, description="syntax node this alias occupies within the statement"
        )
        module_node: NodeRef | None = Field(
            default=None, description="syntax node naming the imported module"
        )
        references: list[NodeRef] = Field(
            default=[], description="syntax nodes where the bound name is read in its own module"
        )
        relative_level: NonNegativeInt = Field(
            default=0, description="number of leading dots the import states, zero when absolute"
        )
        reference_count: NonNegativeInt = Field(
            default=0, description="number of qualifying reads found for the bound name"
        )

    class Role(Source):
        """Retain qualifying use, external, export, type, and ownership roles."""

        has_qualifying_use: bool = Field(
            default=False, description="whether the bound name has at least one qualifying read"
        )
        is_external: bool = Field(
            default=False,
            description="whether the import's root package is outside this repository",
        )
        is_reexported: bool = Field(
            default=False,
            description="whether the name is listed in `__all__` or aliased to itself",
        )
        is_type_only: bool = Field(
            default=False,
            description="whether the import is written only inside a type-checking block",
        )
        has_documented_side_effect: bool = Field(
            default=False,
            description="whether the import is guarded by a try except import handler",
        )
        is_relative: bool = Field(
            default=False, description="whether the import states at least one leading dot"
        )
        is_project_owned: bool = Field(
            default=False,
            description="whether the import is relative or its root package matches the module's",
        )

    class Visibility(Role):
        """Retain sole binding, private component, and wildcard evidence."""

        is_sole_binding: bool = Field(
            default=False, description="whether this import statement binds exactly one name"
        )
        has_private_module_component: bool = Field(
            default=False,
            description="whether a dotted module component starts with an underscore",
        )
        is_private_member: bool = Field(
            default=False, description="whether the imported name starts with a single underscore"
        )
        is_private_uppercase_constant: bool = Field(
            default=False,
            description="whether the private imported name is all uppercase after its underscore",
        )
        is_wildcard: bool = Field(
            default=False, description="whether the import is a wildcard `from module import *`"
        )
