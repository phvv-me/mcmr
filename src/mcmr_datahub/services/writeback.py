from patos import FrozenModel

from mcmr.plugins import NonEmptyStr


class DataHubWriteback(FrozenModel):
    """Say when a run publishes what it concluded and whose name it publishes under.

    A catalog nobody can find is a catalog nobody reads. An owner and a domain travel with
    everything a run publishes, and both default to something a fresh DataHub already knows about,
    which is what puts a first run on the home page instead of only in search results.
    """

    publish_runs: bool = False
    owner: NonEmptyStr = "datahub"
    domain: NonEmptyStr = "Codebases"
    announce: bool = False
    frontend: str = ""
