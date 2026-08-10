from typing import TYPE_CHECKING

from ..configuration import DataHubPeople
from .labels import owner_urn

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from pydantic import JsonValue

    from mcmr.plugins import ModelSpend, RuleJob

    from ..configuration import DataHubPerson


_BUSINESS = "BUSINESS_OWNER"
_TECHNICAL = "TECHNICAL_OWNER"
_STEWARD = "DATA_STEWARD"

_JUDGED = "contextual"


class DataHubDirectory:
    """State who one published run is attributed to, as users the catalog can actually show.

    Ownership only means something when the owners are real. A human answers for the codebase, an
    agent operates the checks on their behalf, and the model that judged the contextual lane
    curates those answers, so the three carry different ownership rather than one shared account.
    The human and the agent are whoever the project named, and the judge is whichever backend the
    run actually asked, which is why no name here is ever written into this package.
    """

    def __init__(self, people: DataHubPeople, owner: str, spent: ModelSpend) -> None:
        self.people = people
        self.fallback = owner
        self.judge = DataHubPeople.judge(backend=spent.backend, model=spent.model)

    @property
    def actor(self) -> str:
        """Return whoever operated this run, which is the agent when a project named one."""
        return self._identity(self.people.agent) or owner_urn(self.fallback)

    def catalog(self) -> dict[str, JsonValue]:
        """Return the ownership of something MCMR publishes that is not itself a codebase."""
        return self._owned([(owner_urn(self.fallback), _TECHNICAL)])

    def domain(self) -> dict[str, JsonValue]:
        """Return the ownership of the domain one repository files its own graph under."""
        return self._owned(self._business() + [(owner_urn(self.fallback), _TECHNICAL)])

    def entities(self) -> Sequence[dict[str, JsonValue]]:
        """State every person and agent this run is attributed to, so no owner is a bare name."""
        return [self._entity(member) for member in self._cast() if member.named]

    def repository(self) -> dict[str, JsonValue]:
        """Return the ownership one repository's own policy flow carries."""
        return self._owned(self._business() + [(self.actor, _TECHNICAL)])

    def stewardship(self, job: RuleJob, held: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        """Return the ownership one rule job carries, crediting whichever model judged it.

        A rule is one entity every codebase publishes onto, so the judge another codebase already
        credited stays exactly where it is and this run adds its own beside it.
        """
        earlier = self._held(held)
        stated = (
            [(self._identity(self.judge), _STEWARD)]
            if self.judge.named and _JUDGED in job.lanes
            else []
        )
        return self._owned(earlier + stated) if earlier or stated else {}

    def table(self) -> dict[str, JsonValue]:
        """Return the ownership one published fact table carries."""
        return self._owned(self._business() + [(owner_urn(self.fallback), _TECHNICAL)])

    @staticmethod
    def _entity(member: DataHubPerson) -> dict[str, JsonValue]:
        """State one person as the user a reader meets on the Users page."""
        stated: dict[str, JsonValue] = {
            "active": True,
            "displayName": member.display,
            "title": member.title,
        }
        return {
            "urn": owner_urn(member.id),
            "corpUserKey": {"value": {"username": member.id}},
            "corpUserInfo": {"value": stated | ({"email": member.email} if member.email else {})},
        }

    @staticmethod
    def _held(held: Mapping[str, JsonValue]) -> list[tuple[str, str]]:
        """Return the owners one entity already carries, ignoring anything else it states."""
        stated = held.get("owners")
        found: list[tuple[str, str]] = []
        for value in stated if isinstance(stated, list) else []:
            entry = value if isinstance(value, dict) else {}
            owner, role = entry.get("owner"), entry.get("type")
            if isinstance(owner, str) and isinstance(role, str):
                found.append((owner, role))
        return found

    @staticmethod
    def _identity(member: DataHubPerson) -> str:
        """Return where one named person lives in the catalog, or nothing when unnamed."""
        return owner_urn(member.id) if member.named else ""

    def _business(self) -> list[tuple[str, str]]:
        """Return whoever answers for the codebase, which is nobody until a project says so."""
        human = self._identity(self.people.human)
        return [(human, _BUSINESS)] if human else []

    def _cast(self) -> Iterable[DataHubPerson]:
        """Return everyone this run is attributed to, in the order a reader meets them."""
        return (self.people.human, self.people.agent, self.judge)

    def _owned(self, entries: Iterable[tuple[str, str]]) -> dict[str, JsonValue]:
        """State one ownership aspect from the owners and roles a caller collected."""
        owners: list[JsonValue] = [
            {"owner": owner, "type": role} for owner, role in dict.fromkeys(entries)
        ]
        stated: JsonValue = {"owners": owners, "lastModified": {"time": 0, "actor": self.actor}}
        return {"ownership": {"value": stated}}
