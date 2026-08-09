from os import environ
from typing import TYPE_CHECKING

import httpx
from patos import FrozenModel
from pydantic import AnyHttpUrl, JsonValue, PositiveFloat, TypeAdapter

from mcmr.plugins import NonEmptyStr

from .request import DataHubCatalogRequest
from .writeback import DataHubWriteback

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Self

# The server a replayed run reports, so a recorded checkout needs no environment at all.
_RECORDED_SERVER = "http://recorded.invalid"

# The flat option names a project writes, folded into the request they all describe.
_REQUEST = ("query", "page_size", "max_assets", "since")

# The flat option names a project writes about what a completed run leaves behind.
_WRITEBACK = ("publish_runs", "owner", "domain", "announce", "frontend", "people")

# Which nested group each of those flat option names belongs under once the settings are read.
_GROUPS = (("catalog", _REQUEST), ("writeback", _WRITEBACK))

# What a DataHub quickstart serves its front end on when GMS answers on the other one,
# which is the one pairing a project can be spared from writing down.
_QUICKSTART = (":8080", ":9002")

# The hosts a placeholder report URL uses. A link nobody can follow is worse than no
# link, so one of these is read as no destination rather than as a destination.
_PLACEHOLDERS = ("example.invalid", "example.com")


class DataHubSettings(FrozenModel):
    """Validate one stateless DataHub connection and bounded catalog request."""

    server: AnyHttpUrl
    sql_dialect: str = ""
    timeout_seconds: PositiveFloat = 30.0
    recorded: str = ""
    report_url: str = ""
    catalog: DataHubCatalogRequest = DataHubCatalogRequest()
    writeback: DataHubWriteback = DataHubWriteback()

    @property
    def frontend(self) -> str:
        """Return where a reader browses this catalog, which a link has to be absolute about.

        DataHub serves its front end beside GMS in most deployments and on its own port in the
        quickstart, so an unset `frontend` follows the quickstart pairing and anything else states
        the origin outright.
        """
        stated = self.writeback.frontend
        return (stated or str(self.server).rstrip("/")).replace(*_QUICKSTART)

    @property
    def report(self) -> str:
        """Return where this run's report lives, or nothing when that would be a dead link.

        A judged asset keeps whatever link it is given until somebody removes it by hand, so an
        unset or placeholder destination writes no link at all rather than one that answers
        nothing.
        """
        stated = self.report_url.strip()
        return "" if any(host in stated for host in _PLACEHOLDERS) else stated

    @property
    def token(self) -> NonEmptyStr | None:
        """Read an optional bearer token only when the provider is about to connect."""
        return (
            TypeAdapter(NonEmptyStr).validate_python(value)
            if (value := environ.get("DATAHUB_GMS_TOKEN")) is not None
            else None
        )

    @classmethod
    def from_mapping(cls, settings: Mapping[str, JsonValue]) -> Self:
        """Read public options from MCMR config and the server URL from the environment."""
        configured = dict(settings)
        configured["server"] = cls._resolved_server(configured)
        return cls.model_validate(cls._folded_options(configured))

    def connection(self, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
        """Open one connection pool aimed at this server with this project's credentials.

        Both transports need the same pool built the same way, and the three values it takes are
        stated here, so the origin, the timeout, and the bearer token stay one answer rather than
        two copies that can disagree about a trailing slash.
        """
        return httpx.AsyncClient(
            base_url=f"{str(self.server).rstrip('/')}/",
            headers=({"Authorization": f"Bearer {token}"} if (token := self.token) else {}),
            timeout=self.timeout_seconds,
            transport=transport,
        )

    @staticmethod
    def _folded_options(configured: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        """Fold the flat option names a project writes into the two groups they each describe."""
        folded: dict[str, JsonValue] = {
            name: {option: configured[option] for option in group if option in configured}
            for name, group in _GROUPS
        }
        flat = {option for _, group in _GROUPS for option in group}
        return {name: value for name, value in configured.items() if name not in flat} | folded

    @staticmethod
    def _resolved_server(configured: Mapping[str, JsonValue]) -> str:
        """Read where GMS answers, from the settings, then the environment, then a recorded run."""
        recorded = configured.get("recorded")
        fallback = _RECORDED_SERVER if isinstance(recorded, str) and recorded.strip() else None
        server = configured.get("server", environ.get("DATAHUB_GMS_URL", fallback))
        if not isinstance(server, str) or not server.strip():
            raise ValueError(
                "DataHub external rules require `server` in MCMR settings or DATAHUB_GMS_URL"
            )
        return server
