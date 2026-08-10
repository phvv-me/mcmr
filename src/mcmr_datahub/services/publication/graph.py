from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import quote

from ..transport.openapi import DataHubOpenAPI
from .announcement import DataHubAnnouncement
from .directory import DataHubDirectory
from .labels import (
    categories,
    category_entity,
    codebase_urn,
    dataset_urn,
    definitions,
    domain_urn,
    families,
    families_node,
    family_term,
    flow_terms,
    flow_urn,
    job_urn,
    labelled,
    lane_entity,
    lanes,
    owner_urn,
    platform_entity,
    platform_urn,
    rule_label,
    rule_tags,
    rule_terms,
    rule_urn,
    rulebook_terms,
    rulebook_urn,
    schema_field,
    scope_entity,
    scopes,
    table_tags,
    table_terms,
    valued,
    vocabulary_node,
    vocabulary_terms,
)
from .verdicts import RuleVerdicts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import httpx
    from pydantic import JsonValue

    from mcmr.plugins import FactDataset, RuleJob, RuleTimeline, RunGraph

    from ..configuration import DataHubSettings

_EXTRACTION = "extract"

_JOB_TYPE = "MCMR"

_QUALIFIER = "."

_LINKS = 5

_RULEBOOK = "MCMR Rulebook"

_FAILING = "FAILURE"

_MEMORY = "Verdict history"


class DataHubCodeGraph:
    """Publish the fact tables one run consumed and the rules that read them.

    A repository already has a lineage graph, it just never had anywhere to put it. One dataset
    per fact family states what the kernel extracted and how wide it is, one flow states the run,
    and one job per executed rule states which of those tables that rule declared. Every entity is
    keyed by its own URN, so a second run rewrites the same graph rather than growing a new one,
    which is why this needs no read before it writes.
    """

    def __init__(
        self,
        settings: DataHubSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def publish(self, graph: RunGraph) -> list[str]:
        """Write what the graph refers to, then the fact datasets and the flows above them."""
        if not graph.datasets:
            return []
        moment = int(datetime.now(UTC).timestamp() * 1000)
        directory = DataHubDirectory(
            self.settings.writeback.people,
            self.settings.writeback.owner,
            graph.spent,
        )
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            written = await self._foundations(openapi, graph, directory)
            written += await openapi.ingest(
                "dataset",
                [self._dataset(dataset, directory, graph, moment) for dataset in graph.datasets],
            )
            written += await openapi.ingest(
                "dataflow",
                [self._flow(graph, directory), self._rulebook(directory)],
            )
        stated = [
            f"{graph.repository} published {len(graph.datasets)} fact datasets as {written} "
            f"entities owned by {self.settings.writeback.owner} "
            f"in {self.settings.writeback.domain}"
        ]
        return stated + await DataHubAnnouncement(self.settings, self.transport).publish(graph)

    async def summarize(self, graph: RunGraph, timelines: Sequence[RuleTimeline]) -> list[str]:
        """Merge this run into the one job every rule keeps for the whole instance.

        A rule is one entity, so publishing a repository reads what earlier repositories already
        wrote onto it and adds this one rather than replacing it. That union is what lets a rule
        page answer which codebases run it and how much each of them reports. Two repositories
        publishing at the same moment race, and the later write wins.
        """
        if not graph.datasets:
            return []
        verdicts = RuleVerdicts(timelines)
        directory = DataHubDirectory(
            self.settings.writeback.people,
            self.settings.writeback.owner,
            graph.spent,
        )
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            held = await openapi.read("datajob", [rule_urn(job.rule) for job in graph.jobs])
            rules = [
                self._rule(graph, job, verdicts.of(job.rule), held, directory)
                for job in graph.jobs
            ]
            written = await openapi.ingest("datajob", [self._extraction(graph), *rules])
        failing = sum(state["lastResult"] == _FAILING for state in verdicts.stated.values())
        return [
            f"{graph.repository} merged into {written - 1} rules of the MCMR Rulebook, "
            f"{len(verdicts.stated) - failing} passing and {failing} failing here"
        ]

    @staticmethod
    def _aspect(held: Mapping[str, JsonValue], name: str) -> dict[str, JsonValue]:
        """Return the value of one aspect an entity holds, or nothing when it holds none."""
        stated = held.get(name)
        if not isinstance(stated, dict):
            return {}
        value = stated.get("value")
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _domain_entity(
        urn: str,
        *,
        name: str,
        described: str,
        parent: str = "",
    ) -> dict[str, JsonValue]:
        """State one domain, which is a name, the sentence it is browsed by, and where it sits."""
        stated: dict[str, JsonValue] = {"name": name, "description": described}
        held = stated | ({"parentDomain": parent} if parent else {})
        return {"urn": urn, "domainProperties": {"value": held}}

    @staticmethod
    def _kind() -> dict[str, JsonValue]:
        """State that a job belongs to a tool DataHub does not orchestrate itself."""
        return {"type": {"string": _JOB_TYPE}}

    @staticmethod
    def _lineage(*, inputs: list[JsonValue], outputs: list[JsonValue]) -> dict[str, JsonValue]:
        """State which fact tables one job reads and which it writes."""
        stated: dict[str, JsonValue] = {
            "inputDatasets": inputs,
            "outputDatasets": outputs,
        }
        return {"value": stated}

    @staticmethod
    def _merged(held: JsonValue, stated: list[str]) -> list[str]:
        """Return everything a rule already read beside what this repository just gave it."""
        earlier = (
            [item for item in held if isinstance(item, str)] if isinstance(held, list) else []
        )
        return sorted(set(earlier) | set(stated))

    @staticmethod
    def _page(anchor: str, *, frontend: str) -> str:
        """Return where a reader opens the recorded verdicts of one published fact table."""
        return f"{frontend}/dataset/{quote(dataset_urn(anchor), safe='')}/Validation"

    @staticmethod
    def _summed(properties: Mapping[str, str], name: str) -> int:
        """Return one per-repository counter added up across every repository that states it."""
        prefix = f"{name}{_QUALIFIER}"
        return sum(
            int(value)
            for key, value in properties.items()
            if key.startswith(prefix) and value.isdigit()
        )

    @staticmethod
    def _typed(job: RuleJob, properties: Mapping[str, str]) -> dict[str, str]:
        """Return the few things about one rule a reader sorts and filters the whole catalog by."""
        return {
            "lane": job.lane,
            "ruleFamily": job.family,
            "findings": properties.get("totalFindings", ""),
            "tokensSpent": properties.get("totalTokens", ""),
        }

    @classmethod
    def _rollups(cls, properties: Mapping[str, str]) -> dict[str, str]:
        """Return what one rule reports across every repository that publishes it.

        The token total is what sorts a rulebook by cost, so it is summed here for the same
        reason the finding total is, and a rule no model ever answered states none of it.
        """
        results = [
            value
            for name, value in properties.items()
            if name.startswith(f"lastResult{_QUALIFIER}")
        ]
        failing = sum(value == _FAILING for value in results)
        stated = {
            "reposFailing": str(failing),
            "reposPassing": str(len(results) - failing),
            "totalFindings": str(cls._summed(properties, "findings")),
        }
        spent = cls._summed(properties, "tokens")
        return stated | ({"totalTokens": str(spent)} if spent else {})

    def _dataset(
        self,
        dataset: FactDataset,
        directory: DataHubDirectory,
        graph: RunGraph,
        moment: int,
    ) -> dict[str, JsonValue]:
        """State one fact family as a dataset with its columns and the rows this run read."""
        return {
            "urn": dataset_urn(dataset.name),
            "datasetProperties": {
                "value": self._stated(
                    dataset.name,
                    described=dataset.description,
                    properties={"family": dataset.family, "category": dataset.category},
                )
            },
            "schemaMetadata": {
                "value": {
                    "schemaName": dataset.family,
                    "platform": platform_urn(),
                    "version": 0,
                    "hash": "",
                    "platformSchema": {"com.linkedin.schema.OtherSchema": {"rawSchema": ""}},
                    "fields": [schema_field(column) for column in dataset.columns],
                }
            },
            "datasetProfile": {
                "value": {
                    "timestampMillis": moment,
                    "rowCount": dataset.row_count,
                    "columnCount": len(dataset.columns),
                }
            },
            **labelled("dataset"),
            **table_tags(dataset),
            **table_terms(),
            **valued({"codebase": graph.repository}),
            **directory.table(),
            **self._filed(graph),
        }

    def _domains(self, graph: RunGraph, directory: DataHubDirectory) -> list[dict[str, JsonValue]]:
        """State the domain every repository is filed under and the room this one browses in.

        Every codebase landing in one flat domain makes that domain a search result rather than a
        place, so each repository gets its own room under the domain the project configured.
        """
        stated = self.settings.writeback.domain
        return [
            self._domain_entity(
                domain_urn(stated),
                name=stated,
                described="Repositories MCMR publishes as fact tables and rule jobs.",
            ),
            self._domain_entity(
                codebase_urn(graph.repository),
                name=graph.repository,
                described=f"Fact tables and policy runs MCMR publishes for {graph.repository}.",
                parent=domain_urn(stated),
            )
            | directory.domain(),
        ]

    def _extraction(self, graph: RunGraph) -> dict[str, JsonValue]:
        """State the one job that reads the repository and writes every fact table."""
        stated: dict[str, JsonValue] = self._stated(
            _EXTRACTION,
            described=f"Extract repository facts from {graph.repository}.",
            properties={"repository": graph.source or graph.repository},
        )
        return {
            "urn": job_urn(graph.repository, job=_EXTRACTION),
            "dataJobInfo": {"value": stated | self._kind()},
            "dataJobInputOutput": self._lineage(
                inputs=[],
                outputs=[dataset_urn(dataset.name) for dataset in graph.datasets],
            ),
            **labelled("extraction"),
            **valued({"codebase": graph.repository}),
        }

    def _filed(self, graph: RunGraph) -> dict[str, JsonValue]:
        """Return the domain a reader browses one repository's own graph under."""
        return {"domains": {"value": {"domains": [codebase_urn(graph.repository)]}}}

    def _flow(self, graph: RunGraph, directory: DataHubDirectory) -> dict[str, JsonValue]:
        """State one repository's policy run as the flow every job below it belongs to."""
        return {
            "urn": flow_urn(graph.repository),
            "dataFlowInfo": {
                "value": self._stated(
                    graph.repository,
                    described=f"MCMR policy run over {graph.repository}.",
                    properties={},
                )
            },
            **flow_terms(),
            **valued({"codebase": graph.repository}),
            **directory.repository(),
            **self._filed(graph),
        }

    async def _foundations(
        self,
        openapi: DataHubOpenAPI,
        graph: RunGraph,
        directory: DataHubDirectory,
    ) -> int:
        """Write everything the published graph points at but does not itself contain.

        The platform, the people, the typed properties, the domains, the tags and the glossary are
        shared by every codebase, so they are written before anything that refers to them and a
        run only ever writes the ones it actually reached.
        """
        written = await openapi.ingest("dataplatform", [platform_entity()])
        written += await openapi.ingest("corpuser", directory.entities())
        written += await openapi.ingest("structuredproperty", definitions())
        written += await openapi.ingest("domain", self._domains(graph, directory))
        written += await openapi.ingest(
            "tag",
            [
                *(lane_entity(lane) for lane in lanes(graph)),
                *(scope_entity(scope) for scope in scopes(graph)),
                *(category_entity(category) for category in categories(graph)),
            ],
        )
        written += await openapi.ingest("glossarynode", [families_node(), vocabulary_node()])
        return written + await openapi.ingest(
            "glossaryterm",
            [*(family_term(family) for family in families(graph)), *vocabulary_terms()],
        )

    def _properties(
        self,
        repository: str,
        job: RuleJob,
        verdict: Mapping[str, str],
        held: JsonValue,
    ) -> dict[str, str]:
        """Return what every repository running this rule currently reports, this one included."""
        earlier = {
            name: value
            for name, value in (held if isinstance(held, dict) else {}).items()
            if isinstance(value, str)
        }
        anchor = job.tables.primary
        stated = {f"anchor{_QUALIFIER}{repository}": anchor} if anchor else {}
        stated |= {
            f"{name}{_QUALIFIER}{repository}": value for name, value in verdict.items() if value
        }
        merged = earlier | {"callable": job.callable} | stated
        return merged | self._rollups(merged)

    def _remembered(self, properties: Mapping[str, str]) -> dict[str, JsonValue]:
        """Point one rule at the fact table each repository records its verdicts against.

        MCMR mints and rewrites this job on every run, so the links are stated whole from the
        properties rather than through the additive `addLink` a judged asset somebody else owns
        needs, which is also what retires a link a repository no longer publishes.
        """
        anchors = {
            name.split(_QUALIFIER, 1)[1]: value
            for name, value in sorted(properties.items())
            if name.startswith(f"anchor{_QUALIFIER}")
        }
        ordered = sorted(
            anchors,
            key=lambda repository: (
                properties.get(f"lastResult{_QUALIFIER}{repository}") != _FAILING,
                repository,
            ),
        )
        held: list[JsonValue] = [
            {
                "url": self._page(anchors[repository], frontend=self.settings.frontend),
                "description": f"{_MEMORY}{_QUALIFIER}{repository}",
                "createStamp": {
                    "time": 0,
                    "actor": owner_urn(self.settings.writeback.owner),
                },
            }
            for repository in ordered[:_LINKS]
        ]
        return {"institutionalMemory": {"value": {"elements": held}}} if held else {}

    def _rule(
        self,
        graph: RunGraph,
        job: RuleJob,
        verdict: Mapping[str, str],
        held: Mapping[str, Mapping[str, JsonValue]],
        directory: DataHubDirectory,
    ) -> dict[str, JsonValue]:
        """State one rule as the single job every repository running it feeds."""
        existing = held.get(rule_urn(job.rule), {})
        inputs = self._merged(
            self._aspect(existing, "dataJobInputOutput").get("inputDatasets"),
            [dataset_urn(name) for name in job.tables.inputs],
        )
        stated = self._aspect(existing, "dataJobInfo").get("customProperties")
        properties = self._properties(graph.repository, job, verdict, stated)
        described: dict[str, JsonValue] = self._stated(
            job.rule,
            described=job.summary,
            properties=dict(properties),
        )
        return {
            "urn": rule_urn(job.rule),
            "dataJobInfo": {"value": described | self._kind()},
            "dataJobInputOutput": self._lineage(inputs=list(inputs), outputs=[]),
            **rule_label(job.lane),
            **rule_tags(job),
            **rule_terms(job),
            **valued(self._typed(job, properties)),
            **directory.stewardship(job, self._aspect(existing, "ownership")),
            **self._remembered(properties),
        }

    def _rulebook(self, directory: DataHubDirectory) -> dict[str, JsonValue]:
        """State the one flow every rule belongs to, whichever repository ran it."""
        return {
            "urn": rulebook_urn(),
            "dataFlowInfo": {
                "value": self._stated(
                    _RULEBOOK,
                    described="Every rule MCMR enforces, across every codebase it publishes.",
                    properties={},
                )
            },
            **rulebook_terms(),
            **directory.catalog(),
        }

    def _stated(
        self,
        name: str,
        *,
        described: str,
        properties: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        """Return what every published entity says about itself and where it came from."""
        stated: dict[str, JsonValue] = {
            "name": name,
            "description": described,
            "customProperties": properties,
        }
        report = self.settings.report
        return stated | {"externalUrl": report} if report else stated
