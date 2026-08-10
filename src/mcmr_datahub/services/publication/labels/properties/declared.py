from typing import TYPE_CHECKING

from patos import FrozenModel

from mcmr.plugins import NonEmptyStr

from ..identities import property_urn
from .kind import PropertyKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pydantic import JsonValue

# The DataHub value domains a typed property is declared in, one per shape MCMR states.
_VALUE_TYPES = {
    "string": "urn:li:dataType:datahub.string",
    "number": "urn:li:dataType:datahub.number",
}

_ENTITY_TYPES = {
    "dataset": "urn:li:entityType:datahub.dataset",
    "dataFlow": "urn:li:entityType:datahub.dataFlow",
    "dataJob": "urn:li:entityType:datahub.dataJob",
}


class StructuredProperty(FrozenModel):
    """Declare one typed, reusable property MCMR states about what it publishes.

    A custom property is a string in a table nobody can sort, filter, or validate. The same fact
    declared once as a structured property becomes a typed facet every codebase shares, so a
    reader can ask the catalog for every contextual rule or every table that keeps flapping
    without knowing which repository wrote the value.
    """

    name: NonEmptyStr
    display: NonEmptyStr
    description: NonEmptyStr
    kind: PropertyKind = PropertyKind.STRING
    entities: list[str] = []
    allowed: dict[str, str] = {}

    @property
    def urn(self) -> str:
        """Return the one identity this definition keeps for the whole instance."""
        return property_urn(self.name)

    def accepts(self, value: str) -> bool:
        """Whether this property takes the stated value, which its own declared domain decides.

        DataHub rejects a whole entity over one value outside a closed set, so a run states only
        what it can prove belongs and simply says nothing about the rest.
        """
        if self.kind is PropertyKind.NUMBER:
            return value.isdigit()
        return bool(value) and (not self.allowed or value in self.allowed)

    def definition(self) -> dict[str, JsonValue]:
        """State the definition itself, which is written once and reused by every codebase."""
        stated: dict[str, JsonValue] = {
            "qualifiedName": f"mcmr.{self.name}",
            "displayName": self.display,
            "description": self.description,
            "valueType": _VALUE_TYPES[str(self.kind)],
            "cardinality": "SINGLE",
            "entityTypes": [_ENTITY_TYPES[entity] for entity in self.entities],
        }
        return {"urn": self.urn, "propertyDefinition": {"value": stated | self._allowed()}}

    def stated(self, value: str) -> dict[str, JsonValue]:
        """State one value of this property, in the shape its declared domain requires."""
        held: JsonValue = (
            {"double": float(value)} if self.kind is PropertyKind.NUMBER else {"string": value}
        )
        return {"propertyUrn": self.urn, "values": [held]}

    def _allowed(self) -> dict[str, JsonValue]:
        """State the closed set of values this property accepts, when it closes one at all."""
        values: list[JsonValue] = [
            {"value": {"string": value}, "description": description}
            for value, description in self.allowed.items()
        ]
        return {"allowedValues": values} if values else {}


# Every typed property MCMR declares, which is the small set that carries the load a reader
# actually sorts and filters by rather than everything a run happens to know.
_DECLARED = (
    StructuredProperty(
        name="lane",
        display="MCMR Lane",
        description="How a rule reaches its answer, which is what a rulebook is filtered by.",
        entities=["dataJob"],
        allowed={
            "deterministic": "Computed from repository structure alone.",
            "contextual": "Judged by a classification backend the caller configured.",
            "external": "Read from a system outside the repository.",
        },
    ),
    StructuredProperty(
        name="ruleFamily",
        display="MCMR Rule Family",
        description="The family a rule belongs to, which is how the rulebook is grouped.",
        entities=["dataJob"],
    ),
    StructuredProperty(
        name="codebase",
        display="MCMR Codebase",
        description="The repository whose run published this entity.",
        entities=["dataset", "dataFlow", "dataJob"],
    ),
    StructuredProperty(
        name="findings",
        display="MCMR Findings",
        description="How many places a rule currently reports, across every codebase running it.",
        kind=PropertyKind.NUMBER,
        entities=["dataJob"],
    ),
    StructuredProperty(
        name="tokensSpent",
        display="MCMR Tokens Spent",
        description="What every recorded run of a rule has cost its backend, in tokens.",
        kind=PropertyKind.NUMBER,
        entities=["dataJob"],
    ),
    StructuredProperty(
        name="flapScore",
        display="MCMR Flap Score",
        description="How often the noisiest subject in a fact table changed verdict lately.",
        kind=PropertyKind.NUMBER,
        entities=["dataset"],
    ),
)

_BY_NAME = {declared.name: declared for declared in _DECLARED}


def definitions() -> Sequence[dict[str, JsonValue]]:
    """State every typed property MCMR declares, so a first run creates the whole namespace."""
    return [declared.definition() for declared in _DECLARED]


def valued(stated: Mapping[str, str]) -> dict[str, JsonValue]:
    """Attach the typed properties one entity states, skipping every one it leaves unsaid."""
    held: list[JsonValue] = [
        declared.stated(value)
        for name, value in stated.items()
        if (declared := _BY_NAME.get(name)) is not None
        if declared.accepts(value)
    ]
    return {"structuredProperties": {"value": {"properties": held}}} if held else {}
