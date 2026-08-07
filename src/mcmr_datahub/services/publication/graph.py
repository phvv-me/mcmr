from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import quote

from mcmr.plugins import ColumnType

from ..transport.openapi import DataHubOpenAPI
from .announcement import DataHubAnnouncement
from .identities import (
    dataset_urn,
    domain_entity,
    domain_urn,
    flow_urn,
    job_urn,
    owner_urn,
    platform_entity,
    platform_urn,
    rule_urn,
    rulebook_urn,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import httpx
    from pydantic import JsonValue

    from mcmr.plugins import FactColumn, FactDataset, RuleJob, RuleTimeline, RunGraph

    from ..settings import DataHubSettings

# What the run itself is called inside the flow, which is the one job that writes the fact tables
# every rule job then reads.
_EXTRACTION = "extract"

# What DataHub calls a job somebody else's tool owns, which is what every rule here is.
_JOB_TYPE = "MCMR"

# What the UI calls each thing MCMR publishes, so a reader scanning results sees a rule and a fact
# table rather than the generic task and dataset every platform contributes.
_SUBTYPES = {"dataset": "Fact table", "extraction": "Extraction", "rule": "Rule"}

# What separates a rule's own state from the repository it reached that state in.
_QUALIFIER = "."

# How many repositories one rule links to its verdicts before the list stops being a list.
_LINKS = 5

# What the flow holding every rule is called, since it is a catalog rather than a codebase.
_RULEBOOK = "MCMR Rulebook"

# What a verdict that failed is called, which is the one state a reader scans a job list for.
_FAILING = "FAILURE"

# What the link from one rule job to its recorded verdicts is called on the job page.
_MEMORY = "Verdict history"

# The DataHub schema field types each published column domain is stated as.
_FIELD_TYPES = {
    ColumnType.STRING: "StringType",
    ColumnType.NUMBER: "NumberType",
    ColumnType.BOOLEAN: "BooleanType",
}


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
        """Write the platform, the domain, the fact datasets, the run flow, and every rule job."""
        if not graph.datasets:
            return []
        moment = int(datetime.now(UTC).timestamp() * 1000)
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            written = await openapi.ingest("dataplatform", [platform_entity()])
            written += await openapi.ingest(
                "domain",
                [domain_entity(self.settings.writeback.domain)],
            )
            written += await openapi.ingest(
                "dataset",
                [self._dataset(dataset, moment) for dataset in graph.datasets],
            )
            written += await openapi.ingest("dataflow", [self._flow(graph), self._rulebook()])
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
        verdicts = self._verdicts(timelines)
        async with DataHubOpenAPI(self.settings, self.transport) as openapi:
            held = await openapi.read("datajob", [rule_urn(job.rule) for job in graph.jobs])
            rules = [
                self._rule(graph, job, verdicts.get(job.rule, {}), held) for job in graph.jobs
            ]
            written = await openapi.ingest("datajob", [self._extraction(graph), *rules])
        failing = sum(state["lastResult"] == _FAILING for state in verdicts.values())
        return [
            f"{graph.repository} merged into {written - 1} rules of the MCMR Rulebook, "
            f"{len(verdicts) - failing} passing and {failing} failing here"
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
    def _field(column: FactColumn) -> dict[str, JsonValue]:
        """State one flattened fact column as the nested schema path DataHub already models."""
        return {
            "fieldPath": column.path,
            "nativeDataType": column.native,
            "description": column.description,
            "type": {"type": {f"com.linkedin.schema.{_FIELD_TYPES[column.data_type]}": {}}},
        }

    @staticmethod
    def _kind() -> dict[str, JsonValue]:
        """State that a job belongs to a tool DataHub does not orchestrate itself."""
        return {"type": {"string": _JOB_TYPE}}

    @staticmethod
    def _labelled(kind: str) -> dict[str, JsonValue]:
        """State what the UI calls one published entity instead of its generic entity type."""
        return {"subTypes": {"value": {"typeNames": [_SUBTYPES[kind]]}}}

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
    def _rollups(properties: Mapping[str, str]) -> dict[str, str]:
        """Return what one rule reports across every repository that publishes it."""
        results = [
            value
            for name, value in properties.items()
            if name.startswith(f"lastResult{_QUALIFIER}")
        ]
        counted = [
            int(value)
            for name, value in properties.items()
            if name.startswith(f"findings{_QUALIFIER}") and value.isdigit()
        ]
        failing = sum(value == _FAILING for value in results)
        return {
            "reposFailing": str(failing),
            "reposPassing": str(len(results) - failing),
            "totalFindings": str(sum(counted)),
        }

    @staticmethod
    def _verdicts(timelines: Sequence[RuleTimeline]) -> dict[str, dict[str, str]]:
        """Return what each rule's recorded timeline currently states, by rule identity.

        One rule keeps a repository-wide timeline beside one per file it reported, and the
        repository-wide one is the state of the rule itself, so a rule naming files is still
        summarized by the timeline that closes when the whole rule stops failing.
        """
        summarized: dict[str, dict[str, str]] = {}
        for timeline in sorted(timelines, key=lambda item: bool(item.where)):
            recorded = timeline.events[-1] if timeline.events else None
            if timeline.rule in summarized or recorded is None:
                continue
            began = timeline.since or recorded.at
            summarized[timeline.rule] = {
                "lastResult": str(timeline.state).upper(),
                "lastRun": recorded.at.isoformat(timespec="seconds"),
                "since": began.isoformat(timespec="seconds"),
                "findings": recorded.properties.get("findings", "0"),
            }
        return summarized

    def _dataset(self, dataset: FactDataset, moment: int) -> dict[str, JsonValue]:
        """State one fact family as a dataset with its columns and the rows this run read."""
        return {
            "urn": dataset_urn(dataset.name),
            "datasetProperties": {
                "value": self._stated(
                    dataset.name,
                    described=dataset.description,
                    properties={"family": dataset.family},
                )
            },
            "schemaMetadata": {
                "value": {
                    "schemaName": dataset.family,
                    "platform": platform_urn(),
                    "version": 0,
                    "hash": "",
                    "platformSchema": {"com.linkedin.schema.OtherSchema": {"rawSchema": ""}},
                    "fields": [self._field(column) for column in dataset.columns],
                }
            },
            "datasetProfile": {
                "value": {
                    "timestampMillis": moment,
                    "rowCount": dataset.row_count,
                    "columnCount": len(dataset.columns),
                }
            },
            **self._labelled("dataset"),
            **self._governance(),
        }

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
            **self._labelled("extraction"),
        }

    def _flow(self, graph: RunGraph) -> dict[str, JsonValue]:
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
            **self._governance(),
        }

    def _governance(self) -> dict[str, JsonValue]:
        """Return the owner and domain a reader browses the published graph by.

        A catalog entity nobody owns and nothing files reaches no home page section, so every
        dataset and the flow above them carry both rather than only being searchable.
        """
        owner = owner_urn(self.settings.writeback.owner)
        return {
            "ownership": {
                "value": {
                    "owners": [{"owner": owner, "type": "TECHNICAL_OWNER"}],
                    "lastModified": {"time": 0, "actor": owner},
                }
            },
            "domains": {"value": {"domains": [domain_urn(self.settings.writeback.domain)]}},
        }

    def _owned(self) -> dict[str, JsonValue]:
        """Return the owner of something MCMR publishes that is not itself a codebase."""
        owner = owner_urn(self.settings.writeback.owner)
        return {
            "ownership": {
                "value": {
                    "owners": [{"owner": owner, "type": "TECHNICAL_OWNER"}],
                    "lastModified": {"time": 0, "actor": owner},
                }
            }
        }

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
        stated = {f"anchor{_QUALIFIER}{repository}": job.primary} if job.primary else {}
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
    ) -> dict[str, JsonValue]:
        """State one rule as the single job every repository running it feeds."""
        existing = held.get(rule_urn(job.rule), {})
        inputs = self._merged(
            self._aspect(existing, "dataJobInputOutput").get("inputDatasets"),
            [dataset_urn(name) for name in job.inputs],
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
            **self._labelled("rule"),
            **self._remembered(properties),
        }

    def _rulebook(self) -> dict[str, JsonValue]:
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
            **self._owned(),
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
