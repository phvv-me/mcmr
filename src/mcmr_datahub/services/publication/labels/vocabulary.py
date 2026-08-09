from typing import TYPE_CHECKING

from mcmr.plugins import ColumnType

from .identities import platform_urn

if TYPE_CHECKING:
    from pydantic import JsonValue

    from mcmr.plugins import FactColumn

# What the UI calls each thing MCMR publishes, so a reader scanning results sees a rule and a fact
# table rather than the generic task and dataset every platform contributes.
_SUBTYPES = {
    "dataset": "Fact table",
    "extraction": "Extraction",
    "rule": "Rule",
    "run": "Policy run",
}
# What the UI calls a rule that leads with one known lane, since the lane is the first thing a
# reader has to know about it. A lane this vocabulary never heard of leaves the plain label.
_RULE_TYPES = {
    "deterministic": "Deterministic rule",
    "contextual": "Contextual rule",
    "external": "External rule",
}
# DataHub's web UI does not consistently render data URI logos. The repository asset is public,
# stable across documentation hosts, and can be cached like other platform marks.
_PLATFORM_LOGO = "https://raw.githubusercontent.com/phvv-me/mcmr/main/docs/assets/icon.png"

# The DataHub schema field types each published column domain is stated as.
_FIELD_TYPES = {
    ColumnType.STRING: "StringType",
    ColumnType.NUMBER: "NumberType",
    ColumnType.BOOLEAN: "BooleanType",
}


def labelled(kind: str) -> dict[str, JsonValue]:
    """State what the UI calls one published entity instead of its generic entity type."""
    return {"subTypes": {"value": {"typeNames": [_SUBTYPES[kind]]}}}


def rule_label(lane: str) -> dict[str, JsonValue]:
    """State what the UI calls one rule, which is the lane it leads with when that is known."""
    return {"subTypes": {"value": {"typeNames": [_RULE_TYPES.get(lane, _SUBTYPES["rule"])]}}}


def platform_entity() -> dict[str, JsonValue]:
    """State the platform every entity below it is attributed to, mark included."""
    return {
        "urn": platform_urn(),
        "dataPlatformInfo": {
            "value": {
                "name": "mcmr",
                "displayName": "MCMR",
                "type": "OTHERS",
                "datasetNameDelimiter": "/",
                "logoUrl": _PLATFORM_LOGO,
            }
        },
    }


def schema_field(column: FactColumn) -> dict[str, JsonValue]:
    """State one flattened fact column as the nested schema path DataHub already models."""
    return {
        "fieldPath": column.path,
        "nativeDataType": column.native,
        "description": column.description,
        "type": {"type": {f"com.linkedin.schema.{_FIELD_TYPES[column.data_type]}": {}}},
    }
