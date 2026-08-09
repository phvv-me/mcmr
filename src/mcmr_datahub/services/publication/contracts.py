from typing import TYPE_CHECKING

from .labels import assertion_urn, contract_id, dataset_urn

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mcmr.plugins import RunGraph, RunRecord

    from ..transport.graphql import DataHubGraphQL


class DataHubContracts:
    """Hold every published fact table to the rules that judge the whole of it.

    A dataset with a hundred assertion timelines under it says what happened. A contract says what
    is promised, which is the question a consumer of the table is actually asking, and DataHub
    renders it on the table's own page rather than in a list somebody has to interpret. The
    promise here is exactly the repository-wide verdict of every rule that read the table, so a
    rule reporting one file keeps its own timeline while the contract stays about the table.

    The contract key is derived from the table, so a later run updates the same contract instead
    of stacking a second one beside it, and the clauses are only ever written after the assertions
    they name exist, because DataHub resolves each one before it accepts the contract.
    """

    upsert = """mutation MCMRUpsertDataContract(
  $entity: String!
  $id: String!
  $quality: [DataQualityContractInput!]
) {
  upsertDataContract(
    input: {entityUrn: $entity, id: $id, state: ACTIVE, dataQuality: $quality}
  ) {
    urn
  }
}"""

    def __init__(self, gateway: DataHubGraphQL) -> None:
        self.gateway = gateway

    async def publish(self, graph: RunGraph, records: Sequence[RunRecord]) -> list[str]:
        """Write one contract per published fact table, out of the rules that judged it whole."""
        promised = {
            dataset.name: self._clauses(dataset_urn(dataset.name), records)
            for dataset in graph.datasets
        }
        written = [name for name, clauses in promised.items() if clauses]
        for name in written:
            await self.gateway.execute(
                self.upsert,
                {
                    "entity": dataset_urn(name),
                    "id": contract_id(name),
                    "quality": [{"assertionUrn": urn} for urn in promised[name]],
                },
                "MCMRUpsertDataContract",
            )
        if not written:
            return []
        clauses = sum(len(promised[name]) for name in written)
        return [
            f"{graph.repository} contracted {len(written)} fact tables on {clauses} rule clauses"
        ]

    @staticmethod
    def _clauses(subject: str, records: Sequence[RunRecord]) -> list[str]:
        """Return the assertion of every rule that judged this whole table, in stable order.

        A verdict naming a file is about that file rather than about the table, so it stays out
        of the promise the table itself makes.
        """
        found = {
            assertion_urn(record): None
            for record in sorted(records, key=lambda item: item.rule)
            if dataset_urn(record.subject) == subject and not record.path
        }
        return list(found)
