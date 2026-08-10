import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

from patos import FrozenModel
from pydantic import JsonValue, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import MutableMapping, Sequence

    from ..batch import BatchProtocol
    from ..candidate import CandidateProtocol

_JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
_JSON_MAPPING = TypeAdapter(dict[str, JsonValue])


class RepositoryEvidence(FrozenModel):
    """Carry one interned evidence and candidate graph with its compact identities."""

    payloads: dict[str, JsonValue]
    identities: dict[str, str]
    candidates: dict[str, JsonValue]
    candidate_aliases: list[list[str]]

    @classmethod
    def of(cls, batches: Sequence[BatchProtocol]) -> RepositoryEvidence:
        """Intern claims and candidates once across every repository rule."""
        payloads: dict[str, JsonValue] = {}
        identities: dict[str, str] = {}
        evidence_keys: dict[str, str] = {}
        candidates: dict[str, JsonValue] = {}
        candidate_keys: dict[str, str] = {}
        grouped: list[list[str]] = []
        for batch in batches:
            aliases: list[str] = []
            for protocol in batch.protocols:
                evidence_aliases = cls._intern_claims(
                    protocol,
                    payloads=payloads,
                    identities=identities,
                    keys=evidence_keys,
                )
                candidate = cls._candidate(protocol, evidence_aliases)
                key = cls._serialized(candidate)
                alias = candidate_keys.setdefault(key, f"c{len(candidate_keys)}")
                candidates.setdefault(alias, candidate)
                aliases.append(alias)
            grouped.append(aliases)
        compact_payloads = _JSON_MAPPING.validate_python(cls._without_nulls(payloads))
        compact_candidates = _JSON_MAPPING.validate_python(cls._without_nulls(candidates))
        return cls(
            payloads=compact_payloads,
            identities=identities,
            candidates=compact_candidates,
            candidate_aliases=grouped,
        )

    @staticmethod
    def _candidate(
        protocol: CandidateProtocol,
        aliases: Sequence[str],
    ) -> dict[str, JsonValue]:
        """Keep only subject data that retained evidence cannot reconstruct."""
        payload: dict[str, JsonValue] = {"e": _JSON_VALUE.validate_python(list(aliases))}
        subject = protocol.candidate.prompt_subject
        match subject:
            case Mapping() as mapping:
                mapping = _JSON_MAPPING.validate_python(mapping)
            case _:
                payload["s"] = subject
                return payload
        details = [
            RepositoryEvidence._structured(claim.detail)
            for claim in protocol.candidate.retained.values()
        ]
        if (fields := mapping.get("fields")) is not None and fields not in details:
            payload["f"] = fields
        match mapping.get("records"):
            case list() as records if any(
                not RepositoryEvidence._known_record(record, protocol.evidence)
                for record in records
            ):
                payload["r"] = records
        if (values := mapping.get("values")) not in (None, []):
            payload["v"] = values
        return payload

    @staticmethod
    def _intern_claims(
        protocol: CandidateProtocol,
        *,
        payloads: MutableMapping[str, JsonValue],
        identities: MutableMapping[str, str],
        keys: MutableMapping[str, str],
    ) -> list[str]:
        """Intern one candidate's claims and return their compact aliases."""
        aliases: list[str] = []
        for identifier, claim in protocol.candidate.retained.items():
            payload: dict[str, JsonValue] = {
                "d": RepositoryEvidence._structured(claim.detail),
                "s": claim.source,
            }
            if claim.confidence != 1.0:
                payload["p"] = claim.confidence
            key = RepositoryEvidence._serialized({"id": identifier, **payload})
            alias = keys.setdefault(key, f"e{len(keys)}")
            payloads.setdefault(alias, payload)
            identities.setdefault(alias, identifier)
            aliases.append(alias)
        return aliases

    @staticmethod
    def _known_record(record: JsonValue, evidence: Mapping[str, JsonValue]) -> bool:
        """Whether one record is a retained evidence identity."""
        match record:
            case str() as identifier:
                return identifier in evidence
            case _:
                return False

    @staticmethod
    def _serialized(value: JsonValue | Mapping[str, JsonValue]) -> str:
        """Render one stable compact JSON value for interning."""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _structured(detail: str) -> JsonValue:
        """Avoid quoting and escaping evidence that is already valid JSON."""
        try:
            return _JSON_VALUE.validate_json(detail)
        except ValidationError:
            return detail

    @staticmethod
    def _without_nulls(value: JsonValue) -> JsonValue:
        """Drop unknown mapping fields while retaining every explicit non-null value."""
        match value:
            case dict() as mapping:
                return {
                    key: RepositoryEvidence._without_nulls(item)
                    for key, item in mapping.items()
                    if item is not None
                }
            case list() as items:
                return [RepositoryEvidence._without_nulls(item) for item in items]
            case _:
                return value
