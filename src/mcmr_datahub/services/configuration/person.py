from patos import FrozenModel

_ANONYMOUS = ""


class DataHubPerson(FrozenModel):
    """Name one person or agent a published run is attributed to.

    A catalog full of work nobody signed is a catalog nobody trusts. The identity is what every
    ownership record points at, and the display name and title are what make the Users page read
    like a team rather than a list of usernames. A project that names nobody publishes nobody,
    because inventing a person would be worse than leaving the credit unstated.
    """

    id: str = _ANONYMOUS
    name: str = _ANONYMOUS
    email: str = _ANONYMOUS
    title: str = _ANONYMOUS

    @property
    def display(self) -> str:
        """Return what a reader sees, which falls back to the identity when no name is given."""
        return self.name.strip() or self.id.strip()

    @property
    def named(self) -> bool:
        """Whether a project actually named this person, which is what licenses publishing one."""
        return bool(self.id.strip())
