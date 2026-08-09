from typing import TYPE_CHECKING

from pydantic import Field

from ...foundation import Fact

if TYPE_CHECKING:
    from .match import AuthorshipMatch


class AuthorshipSignalFact(Fact):
    """Describe exact style matches from an explicitly enabled analyzer."""

    external_evidence = True
    matches: list[AuthorshipMatch] = Field(
        default=[], description="authorship style matches reported by the external analyzer"
    )
