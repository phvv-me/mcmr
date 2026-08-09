import re
from typing import TYPE_CHECKING

from ...domain.contracts import FactDataset, RuleJob, RuleTables, RunGraph
from .columns import fact_columns

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from patos import FrozenModel

    from ...domain.contracts import ModelSpend
    from ...rulebook.catalog import RuleDefinition
    from ...table import RepositoryTables, Table
    from ...table.runtime.table import TableFamily
    from ..engine.prepared import PreparedRule

# Where a repository publishes its own fact tables, which keeps them apart from the warehouse
# datasets a catalog already holds under some other platform.
_NAMESPACE = "facts"

# Where every fact family is defined, whose next path step is the group the family belongs to.
_DEFINED = "mcmr.facts."


class RunGraphBuilder:
    """Collect the fact tables one run materialized and the rules that read them.

    Every input is already in hand while a batch runs, so the graph is a projection of the run
    rather than a second pass over the repository. A family reached by several batches is
    described once, because the table behind it is the same table.
    """

    def __init__(self, repository: Path, source: str = "") -> None:
        self.repository = repository.resolve().name
        self.source = source
        self.datasets: dict[str, FactDataset] = {}
        self.jobs: dict[str, RuleJob] = {}

    @staticmethod
    def family_category(family: type[FrozenModel]) -> str:
        """Return the fact group one family is defined under, which is how a reader browses it.

        The groups are the directories under `mcmr.facts`, so `structure`, `program`, `project`,
        `symbols`, `testing` and `languages` come straight from where the model already lives
        rather than from a second taxonomy somebody has to keep in step with it.
        """
        module = family.__module__
        if not module.startswith(_DEFINED):
            return ""
        return module.removeprefix(_DEFINED).split(".", 1)[0]

    @staticmethod
    def family_slug(family: type[FrozenModel]) -> str:
        """Return the snake-case name one fact family is published under.

        An acronym stays one word, so `CIConfigurationFact` is `ci_configuration_fact` rather
        than the letter-by-letter split a naive boundary would produce.
        """
        boundary = r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
        return re.sub(boundary, "_", family.__name__).lower()

    def dataset_name(self, family: type[FrozenModel]) -> str:
        """Return the dataset identity one fact family carries inside this repository."""
        return f"{self.repository}/{_NAMESPACE}/{self.family_slug(family)}"

    def graph(self) -> RunGraph:
        """Return the complete graph in stable dataset and rule order."""
        return RunGraph(
            repository=self.repository,
            source=self.source,
            datasets=[self.datasets[name] for name in sorted(self.datasets)],
            jobs=[self.jobs[rule] for rule in sorted(self.jobs)],
        )

    def record(
        self,
        tables: RepositoryTables,
        rules: Sequence[PreparedRule],
        definitions: Mapping[str, RuleDefinition],
        *,
        spend: Mapping[str, Mapping[str, ModelSpend]],
    ) -> None:
        """Describe the tables one batch materialized and the rules that just read them.

        spend: what each rule paid its contextual backend, at every file that rule read.
        """
        for family in tables:
            name = self.dataset_name(family)
            self.datasets.setdefault(name, self._dataset(family, name, tables[family]))
        for rule in rules:
            definition = definitions[rule.path]
            self.jobs[definition.id] = self._job(rule, definition, spend.get(rule.path, {}))

    def _dataset(
        self,
        family: type[TableFamily],
        name: str,
        table: Table[TableFamily],
    ) -> FactDataset:
        """Describe one fact family as the dataset its verdicts anchor on."""
        identity = next(iter(table.relation_type))
        return FactDataset(
            family=family.__name__,
            name=name,
            category=self.family_category(family),
            description=(family.__doc__ or "").strip().splitlines()[0],
            columns=list(fact_columns(family)),
            row_count=table.frame(identity).height,
        )

    def _job(
        self,
        rule: PreparedRule,
        definition: RuleDefinition,
        spend: Mapping[str, ModelSpend],
    ) -> RuleJob:
        """Describe one executed rule as the job that read its declared fact datasets."""
        return RuleJob(
            rule=definition.id,
            callable=rule.path,
            summary=definition.documentation.summary,
            tables=RuleTables(
                inputs=sorted({self.dataset_name(family) for _, family in rule.rule.tables}),
                primary=self.dataset_name(rule.primary_family),
            ),
            lanes=[str(definition.lane), *(["external"] if definition.external else [])],
            family=definition.family,
            spend=dict(spend),
        )
