from typing import TYPE_CHECKING

from pydantic import JsonValue, NonNegativeInt, TypeAdapter

from mcmr.facts import (
    DataAsset,
    DataAssetFact,
    DataAssetReferenceFact,
    DataField,
    DataFieldReferenceFact,
    LineageEdge,
    LineageEdgeFact,
    SourceSpan,
    StringExpressionFact,
)
from mcmr.plugins import (
    Fact,
    FactProvider,
    HistoryContext,
    ProviderContext,
    PublicationContext,
    RepositoryTables,
    fact_table,
    provider,
)

from .publication import DataHubCodeGraph
from .queries import DataHubCatalogQueries
from .recording import DataHubRecording
from .resolution.catalog import DataHubCatalog
from .resolution.references import SQLReferenceExtractor
from .settings import DataHubSettings
from .transport.graphql import DataHubGraphQL
from .transport.recorded import RecordedTransport

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path
    from typing import ClassVar

    import httpx

    from mcmr.plugins import RuleTimeline

    from .request import DataHubCatalogRequest


@provider
class DataHubProvider(FactProvider):
    """Supply governed DataHub assets directly through its GraphQL API."""

    families: ClassVar[dict[type[Fact], set[type[Fact]]]] = {
        DataAssetFact: set(),
        DataAssetReferenceFact: {StringExpressionFact},
        DataFieldReferenceFact: {StringExpressionFact},
        LineageEdgeFact: set(),
    }

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def history(self, context: HistoryContext) -> list[RuleTimeline]:
        """Return every verdict DataHub already holds for the assets a repository names.

        This is the read an agent performs before it changes anything. It judges nothing and
        writes nothing, so a repository with no recorded runs simply comes back empty.
        """
        settings = DataHubSettings.from_mapping(context.settings)
        transport = self._transport(context.repository, settings)
        async with DataHubGraphQL(settings, transport) as gateway:
            assertions = DataHubRecording(gateway, settings.report)
            return [
                timeline
                for subject in context.subjects
                for timeline in await assertions.read(subject)
            ]

    async def publish(self, context: PublicationContext) -> list[str]:
        """Publish the graph this run consumed, then record every verdict against it.

        DataHub already models a check an external tool owns, so each rule and subject pair becomes
        one custom assertion a later run lands on again. A verdict about ordinary source needs a
        subject first, which is why this publishes the fact tables the run read before recording.
        """
        settings = DataHubSettings.from_mapping(context.settings)
        transport = self._transport(context.repository, settings)
        published = await DataHubCodeGraph(settings, transport).publish(context.graph)
        judged = context.records
        subjects = list(dict.fromkeys(record.subject for record in judged))
        async with DataHubGraphQL(settings, transport) as gateway:
            recording = DataHubRecording(gateway, settings.report)
            await recording.record(judged)
            closed = await recording.reconcile(
                subjects,
                judged,
                repository=context.graph.repository,
            )
            receipts = [
                await recording.receipt(subject, judged, label=context.label)
                for subject in subjects
            ]
            recorded = [line for subject in subjects for line in await recording.read(subject)]
        summary = await DataHubCodeGraph(settings, transport).summarize(context.graph, recorded)
        return [*published, *summary, *closed, *receipts]

    async def tables(self, context: ProviderContext) -> RepositoryTables:
        """Build exactly the requested catalog tables without retained local state."""
        if not context.requested <= set(self.families):
            raise RuntimeError("DataHub provider received a family it does not own")
        settings = DataHubSettings.from_mapping(context.settings)
        transport = self._transport(context.repository, settings)
        async with DataHubGraphQL(settings, transport) as gateway:
            assets = await self._assets(gateway, settings.catalog)
            renames = await self._requested_renames(gateway, context, assets)
            edges = await self._requested_edges(gateway, context, assets, settings.catalog)
        tables = RepositoryTables()
        for family, facts in (
            (DataAssetFact, [self._asset_fact(assets)]),
            (LineageEdgeFact, [self._lineage_fact(edges)]),
        ):
            if family in context.requested:
                tables.add(fact_table(family, facts))
        if context.requested & {DataAssetReferenceFact, DataFieldReferenceFact}:
            self._add_reference_tables(tables, context, assets, settings, renames)
        return tables

    @staticmethod
    def _asset_fact(assets: list[DataAsset]) -> DataAssetFact:
        """Retain one complete bounded catalog snapshot."""
        return DataAssetFact(
            key="datahub-assets",
            span=SourceSpan(path="datahub"),
            assets=assets,
        )

    @staticmethod
    def _lineage_fact(edges: list[LineageEdge]) -> LineageEdgeFact:
        """Retain one complete bounded downstream lineage snapshot."""
        return LineageEdgeFact(
            key="datahub-lineage",
            span=SourceSpan(path="datahub"),
            edges=edges,
        )

    @staticmethod
    def _mapping(value: JsonValue) -> dict[str, JsonValue]:
        """Validate one required GraphQL object."""
        return TypeAdapter(dict[str, JsonValue]).validate_python(value)

    @staticmethod
    def _recording(repository: Path, recorded: str) -> Path:
        """Resolve one recording directory the checked configuration names."""
        root = repository / recorded
        if not root.is_dir():
            raise ValueError(f"the DataHub recording directory {recorded} does not exist")
        return root

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

    def _add_reference_tables(
        self,
        tables: RepositoryTables,
        context: ProviderContext,
        assets: list[DataAsset],
        settings: DataHubSettings,
        renames: dict[str, dict[str, str]],
    ) -> None:
        """Resolve and add only the requested source reference families."""
        asset_references, field_references = SQLReferenceExtractor(
            catalog=DataHubCatalog(assets=assets),
            dialect=settings.sql_dialect,
            renames=renames,
        ).facts(context.table(StringExpressionFact))
        if DataAssetReferenceFact in context.requested:
            tables.add(fact_table(DataAssetReferenceFact, asset_references))
        if DataFieldReferenceFact in context.requested:
            tables.add(fact_table(DataFieldReferenceFact, field_references))

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

    async def _assets(
        self,
        gateway: DataHubGraphQL,
        request: DataHubCatalogRequest,
    ) -> list[DataAsset]:
        """Read catalog pages until the configured request bound or catalog end."""
        assets: list[DataAsset] = []
        while len(assets) < request.max_assets:
            count = min(request.page_size, request.max_assets - len(assets))
            page, total = await self._page(gateway, request, start=len(assets), count=count)
            assets.extend(page)
            if not page or len(assets) >= total:
                break
        return assets

    def _domain(self, domain: Mapping[str, JsonValue]) -> str:
        """Prefer a human domain name while retaining its URN as a fallback."""
        nested = self._optional_mapping(domain, "domain")
        properties = self._optional_mapping(nested, "properties")
        return self._text(properties.get("name")) or self._text(nested.get("urn"))

    async def _edges(
        self,
        gateway: DataHubGraphQL,
        assets: Sequence[DataAsset],
        page_size: int,
    ) -> list[LineageEdge]:
        """Read the direct downstream neighbour of every asset as one resolved lineage edge."""
        known = {asset.identifier for asset in assets}
        edges: list[LineageEdge] = []
        for asset in assets:
            data = await gateway.execute(
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
        gateway: DataHubGraphQL,
        request: DataHubCatalogRequest,
        *,
        start: int,
        count: int,
    ) -> tuple[list[DataAsset], int]:
        """Read and project one exact DataHub search page."""
        data = await gateway.execute(
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

    async def _renames(
        self,
        gateway: DataHubGraphQL,
        assets: Sequence[DataAsset],
    ) -> dict[str, dict[str, str]]:
        """Read the column renames each asset's own fine-grained lineage proves."""
        proven: dict[str, dict[str, str]] = {}
        for asset in assets:
            data = await gateway.execute(
                DataHubCatalogQueries.field_lineage,
                {"urn": asset.identifier},
                "MCMRFieldLineage",
            )
            if renamed := self._renamed_fields(asset, self._optional_mapping(data, "dataset")):
                proven[asset.identifier] = renamed
        return proven

    async def _requested_edges(
        self,
        gateway: DataHubGraphQL,
        context: ProviderContext,
        assets: Sequence[DataAsset],
        request: DataHubCatalogRequest,
    ) -> list[LineageEdge]:
        """Read downstream lineage only when a selected rule declared the family."""
        if LineageEdgeFact not in context.requested:
            return []
        return await self._edges(gateway, assets, request.page_size)

    async def _requested_renames(
        self,
        gateway: DataHubGraphQL,
        context: ProviderContext,
        assets: Sequence[DataAsset],
    ) -> dict[str, dict[str, str]]:
        """Read column lineage only when a selected rule declared the field family."""
        if DataFieldReferenceFact not in context.requested:
            return {}
        return await self._renames(gateway, assets)

    def _transport(
        self,
        repository: Path,
        settings: DataHubSettings,
    ) -> httpx.AsyncBaseTransport | None:
        """Prefer an injected transport, then a recording, then the live network."""
        if self.transport is not None:
            return self.transport
        return (
            RecordedTransport(self._recording(repository, settings.recorded))
            if settings.recorded
            else None
        )
