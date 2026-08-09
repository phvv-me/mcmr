from typing import TYPE_CHECKING

from pydantic import JsonValue, NonNegativeInt, TypeAdapter

from mcmr.facts import DataAsset, DataField, LineageEdge

from .queries import DataHubCatalogQueries

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ..configuration import DataHubCatalogRequest
    from ..transport.graphql import DataHubGraphQL


class DataHubAssetReader:
    """Read one bounded catalog snapshot, its lineage, and the renames it proves.

    Everything here answers what DataHub currently holds, which is a different job from deciding
    what a run publishes back. Keeping the read on its own side means a provider states which
    families a rule asked for and nothing about how a search page is paged or how a nullable
    aspect is spelled.
    """

    def __init__(self, gateway: DataHubGraphQL) -> None:
        self.gateway = gateway

    async def assets(self, request: DataHubCatalogRequest) -> list[DataAsset]:
        """Read catalog pages until the configured request bound or catalog end."""
        assets: list[DataAsset] = []
        while len(assets) < request.max_assets:
            count = min(request.page_size, request.max_assets - len(assets))
            page, total = await self._page(request, start=len(assets), count=count)
            assets.extend(page)
            if not page or len(assets) >= total:
                break
        return assets

    async def edges(self, assets: Sequence[DataAsset], page_size: int) -> list[LineageEdge]:
        """Read the direct downstream neighbor of every asset as one resolved lineage edge."""
        known = {asset.identifier for asset in assets}
        edges: list[LineageEdge] = []
        for asset in assets:
            data = await self.gateway.execute(
                DataHubCatalogQueries.lineage,
                {"urn": asset.identifier, "count": page_size, "start": 0},
                "MCMRDataLineage",
            )
            search = self._mapping(data["searchAcrossLineage"])
            edges.extend(
                LineageEdge(
                    source=asset.identifier,
                    target=target,
                    source_exists=asset.identifier in known,
                    target_exists=target in known,
                )
                for target in self._neighbours(search)
            )
        return edges

    async def renames(self, assets: Sequence[DataAsset]) -> dict[str, dict[str, str]]:
        """Read the column renames each asset's own fine-grained lineage proves."""
        proven: dict[str, dict[str, str]] = {}
        for asset in assets:
            data = await self.gateway.execute(
                DataHubCatalogQueries.field_lineage,
                {"urn": asset.identifier},
                "MCMRFieldLineage",
            )
            if renamed := self._renamed_fields(asset, self._optional_mapping(data, "dataset")):
                proven[asset.identifier] = renamed
        return proven

    @staticmethod
    def _mapping(value: JsonValue) -> dict[str, JsonValue]:
        """Validate one required GraphQL object."""
        return TypeAdapter(dict[str, JsonValue]).validate_python(value)

    @staticmethod
    def _sequence(value: JsonValue) -> list[JsonValue]:
        """Validate one required GraphQL list."""
        return TypeAdapter(list[JsonValue]).validate_python(value)

    @staticmethod
    def _text(value: JsonValue | None) -> str:
        """Read nullable GraphQL text without inventing metadata."""
        return value if isinstance(value, str) else ""

    @classmethod
    def _optional_mapping(
        cls,
        parent: Mapping[str, JsonValue],
        key: str,
    ) -> dict[str, JsonValue]:
        """Validate one nullable GraphQL object as an empty mapping when absent."""
        return {} if parent.get(key) is None else cls._mapping(parent[key])

    @classmethod
    def _optional_sequence(
        cls,
        parent: Mapping[str, JsonValue],
        key: str,
    ) -> list[JsonValue]:
        """Validate one nullable GraphQL list as an empty list when absent.

        DataHub spells an empty collection as an explicit `null` whenever the aspect behind it was
        never written, so a selected key is present while its value is not a list.
        """
        return [] if parent.get(key) is None else cls._sequence(parent[key])

    def _asset(self, value: JsonValue, changed_after: int | None) -> DataAsset:
        """Project one DataHub dataset and its governance metadata."""
        entity = self._mapping(value)
        properties = self._optional_mapping(entity, "properties")
        deprecation = self._optional_mapping(entity, "deprecation")
        identifier = self._text(entity["urn"])
        return DataAsset(
            identifier=identifier,
            description=self._text(properties.get("description")),
            owners=self._owners(self._optional_mapping(entity, "ownership")),
            domain=self._domain(self._optional_mapping(entity, "domain")),
            lifecycle="deprecated" if deprecation.get("deprecated") is True else "active",
            is_changed=self._is_changed(properties, changed_after),
            fields=self._fields(self._optional_mapping(entity, "schemaMetadata")),
        )

    def _domain(self, domain: Mapping[str, JsonValue]) -> str:
        """Prefer a human domain name while retaining its URN as a fallback."""
        nested = self._optional_mapping(domain, "domain")
        properties = self._optional_mapping(nested, "properties")
        return self._text(properties.get("name")) or self._text(nested.get("urn"))

    def _fields(self, schema: Mapping[str, JsonValue]) -> list[DataField]:
        """Project schema fields without losing DataHub type, description, or governance labels."""
        return [
            DataField(
                name=self._text(field["fieldPath"]),
                data_type=self._text(field["type"]),
                description=self._text(field.get("description")),
                tags=self._labels(
                    self._optional_mapping(field, "globalTags"),
                    collection="tags",
                    entity="tag",
                ),
                glossary_terms=self._labels(
                    self._optional_mapping(field, "glossaryTerms"),
                    collection="terms",
                    entity="term",
                ),
            )
            for value in self._optional_sequence(schema, "fields")
            if (field := self._mapping(value))
        ]

    def _identity(self, owner: Mapping[str, JsonValue]) -> str:
        """Prefer the concise user or group name while retaining its URN."""
        return (
            self._text(owner.get("username"))
            or self._text(owner.get("name"))
            or self._text(owner.get("urn"))
        )

    def _is_changed(self, properties: Mapping[str, JsonValue], changed_after: int | None) -> bool:
        """Read whether DataHub modified this asset after the configured day."""
        if changed_after is None:
            return False
        modified = self._optional_mapping(properties, "lastModified").get("time")
        return isinstance(modified, int) and modified >= changed_after

    def _label(self, value: JsonValue, entity: str) -> str:
        """Prefer the human label name while retaining its URN as a fallback."""
        labelled = self._mapping(self._mapping(value)[entity])
        properties = self._optional_mapping(labelled, "properties")
        return self._text(properties.get("name")) or self._text(labelled.get("urn"))

    def _labels(
        self,
        association: Mapping[str, JsonValue],
        *,
        collection: str,
        entity: str,
    ) -> list[str]:
        """Read every attached tag or glossary term in stable DataHub response order."""
        return [
            self._label(value, entity)
            for value in self._optional_sequence(association, collection)
        ]

    def _neighbours(self, search: Mapping[str, JsonValue]) -> list[str]:
        """Return only the assets one hop downstream, which is what an edge states."""
        return [
            self._text(self._mapping(result["entity"]).get("urn"))
            for value in self._sequence(search["searchResults"])
            if (result := self._mapping(value))
            if result.get("degree") == 1
        ]

    def _owners(self, ownership: Mapping[str, JsonValue]) -> list[str]:
        """Return each owner identity in stable DataHub response order."""
        return [
            self._identity(self._mapping(self._mapping(entry)["owner"]))
            for entry in self._optional_sequence(ownership, "owners")
        ]

    async def _page(
        self,
        request: DataHubCatalogRequest,
        *,
        start: int,
        count: int,
    ) -> tuple[list[DataAsset], int]:
        """Read and project one exact DataHub search page."""
        data = await self.gateway.execute(
            DataHubCatalogQueries.assets,
            {"query": request.query, "count": count, "start": start},
            "MCMRDataAssets",
        )
        search = self._mapping(data["searchAcrossEntities"])
        results = self._sequence(search["searchResults"])
        changed_after = request.changed_after
        assets = [
            self._asset(self._mapping(result)["entity"], changed_after) for result in results
        ]
        total = TypeAdapter(NonNegativeInt).validate_python(search["total"])
        return assets, total

    def _paths(self, edge: Mapping[str, JsonValue], side: str) -> list[str]:
        """Read the schema field paths one fine-grained lineage edge names on one side."""
        return [
            path
            for value in self._optional_sequence(edge, side)
            if (path := self._text(self._mapping(value).get("path")))
        ]

    def _renamed_fields(
        self,
        asset: DataAsset,
        dataset: Mapping[str, JsonValue],
    ) -> dict[str, str]:
        """Map each retired column to the sole surviving column its lineage derives."""
        declared = {field.name for field in asset.fields}
        successors: dict[str, set[str]] = {}
        for value in self._optional_sequence(dataset, "fineGrainedLineages"):
            edge = self._mapping(value)
            retired = {name for name in self._paths(edge, "upstreams") if name not in declared}
            surviving = {name for name in self._paths(edge, "downstreams") if name in declared}
            for name in retired:
                successors.setdefault(name, set()).update(surviving)
        return {name: next(iter(found)) for name, found in successors.items() if len(found) == 1}
