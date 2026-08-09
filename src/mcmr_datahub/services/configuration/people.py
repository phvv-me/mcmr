from patos import FrozenModel

from .person import DataHubPerson


class DataHubPeople(FrozenModel):
    """Name the cast one repository publishes under, which a project states and never a package.

    The human is who answers for the codebase and the agent is what operates the checks on their
    behalf, so the two carry different ownership rather than sharing one account. The model that
    judges the contextual lane is a third member nobody configures, because it is whatever backend
    the run actually asked, and naming it in configuration would let the two drift apart.
    """

    human: DataHubPerson = DataHubPerson()
    agent: DataHubPerson = DataHubPerson()

    @staticmethod
    def judge(*, backend: str, model: str) -> DataHubPerson:
        """Return the user one contextual backend and model answer as, or nobody when none ran."""
        if not model:
            return DataHubPerson()
        named = f"the {backend} backend" if backend else "a configured backend"
        return DataHubPerson(
            id=model,
            name=model,
            title=f"Contextual judge MCMR reaches through {named}",
        )
