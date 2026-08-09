from typing import TYPE_CHECKING

from mcmr.facts import (
    DataAsset,
    DataAssetFact,
    DataAssetReferenceFact,
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

from .configuration import DataHubSettings
from .publication import (
    DataHubCodeGraph,
    DataHubContracts,
    DataHubIncidents,
    DataHubRunInstance,
)
from .recording import DataHubRecording
from .resolution.assets import DataHubAssetReader
from .resolution.catalog import DataHubCatalog
from .resolution.references import SQLReferenceExtractor
from .transport.graphql import DataHubGraphQL
from .transport.recorded import RecordedTransport

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import ClassVar

    import httpx

    from mcmr.plugins import RuleTimeline

    from .configuration import DataHubCatalogRequest


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
        Each published table is then held to a contract naming the assertions that just landed, so
        the promise renders where a consumer of the table already looks, and the recorded history
        is read back to raise an incident on whatever keeps changing its answer. The invocation
        itself is recorded last, as the process instance under this repository's flow that every
        verdict above already names.
        """
        settings = DataHubSettings.from_mapping(context.settings)
        transport = self._transport(context.repository, settings)
        published = await DataHubCodeGraph(settings, transport).publish(context.graph)
        judged = context.records
        subjects = list(dict.fromkeys(record.subject for record in judged))
        async with DataHubGraphQL(settings, transport) as gateway:
            recording = DataHubRecording(gateway, settings.report, run=context.run)
            await recording.record(judged)
            promised = await DataHubContracts(gateway).publish(context.graph, judged)
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
        raised = await DataHubIncidents(settings, transport).reconcile(
            context.graph,
            recorded,
            judged,
            run=context.run,
        )
        ran = await DataHubRunInstance(settings, transport).publish(
            context.graph,
            context.summary,
            run=context.run,
        )
        return [*published, *promised, *summary, *closed, *receipts, *raised, *ran]

    async def tables(self, context: ProviderContext) -> RepositoryTables:
        """Build exactly the requested catalog tables without retained local state."""
        if not context.requested <= set(self.families):
            raise RuntimeError("DataHub provider received a family it does not own")
        settings = DataHubSettings.from_mapping(context.settings)
        transport = self._transport(context.repository, settings)
        async with DataHubGraphQL(settings, transport) as gateway:
            reader = DataHubAssetReader(gateway)
            assets = await reader.assets(settings.catalog)
            renames = await self._requested_renames(reader, context, assets)
            edges = await self._requested_edges(reader, context, assets, settings.catalog)
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
    def _recording(repository: Path, recorded: str) -> Path:
        """Resolve one recording directory the checked configuration names."""
        root = repository / recorded
        if not root.is_dir():
            raise ValueError(f"the DataHub recording directory {recorded} does not exist")
        return root

    @staticmethod
    async def _requested_edges(
        reader: DataHubAssetReader,
        context: ProviderContext,
        assets: Sequence[DataAsset],
        request: DataHubCatalogRequest,
    ) -> list[LineageEdge]:
        """Read downstream lineage only when a selected rule declared the family."""
        if LineageEdgeFact not in context.requested:
            return []
        return await reader.edges(assets, request.page_size)

    @staticmethod
    async def _requested_renames(
        reader: DataHubAssetReader,
        context: ProviderContext,
        assets: Sequence[DataAsset],
    ) -> dict[str, dict[str, str]]:
        """Read column lineage only when a selected rule declared the field family."""
        if DataFieldReferenceFact not in context.requested:
            return {}
        return await reader.renames(assets)

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
