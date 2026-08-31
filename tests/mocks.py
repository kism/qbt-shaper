"""Pydantic models of the external API payloads we consume, plus fake transports."""

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    import aiohttp

# --- Payloads: one model per endpoint the service clients actually read ---


class JellyfinAuth(BaseModel):
    AccessToken: str = "jellyfin-token"


class JellyfinSession(BaseModel):
    NowPlayingItem: dict[str, Any] | None = None


class DispatcharrToken(BaseModel):
    access: str = "dispatcharr-token"


class DispatcharrStatus(BaseModel):
    count: int = 0


class QbtTransferInfo(BaseModel):
    up_info_speed: int = 0


class QbtTorrent(BaseModel):
    hash: str


class HaState(BaseModel):
    entity_id: str = "device_tracker.phone"
    state: str = "not_home"


# --- Transports ---


class FakeResponse:
    """Stands in for an aiohttp response context manager."""

    def __init__(self, payload: BaseModel | list[BaseModel] | None = None, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def raise_for_status(self) -> None:
        if self.status >= HTTPStatus.BAD_REQUEST:
            msg = f"HTTP {self.status}"
            raise RuntimeError(msg)

    async def json(self):
        assert self._payload is not None, "no payload was queued for this request"
        if isinstance(self._payload, list):
            return [m.model_dump() for m in self._payload]
        return self._payload.model_dump()


class FakeSession:
    """aiohttp.ClientSession stand-in that hands out queued responses in order."""

    def __init__(self, *responses: FakeResponse) -> None:
        self._responses = list(responses)
        self.requests: list[tuple[str, str]] = []

    def _next(self, method: str, url: str) -> FakeResponse:
        self.requests.append((method, url))
        return self._responses.pop(0)

    def get(self, url: str, **_):
        return self._next("GET", url)

    def post(self, url: str, **_):
        return self._next("POST", url)


class FakeQbtClient:
    """qbittorrentapi.Client stand-in, recording everything that was set."""

    def __init__(self, host: str = "http://qbt", username: str = "u", password: str = "p") -> None:
        self.host = host
        self.up_info_speed = 0
        self.torrents: list[QbtTorrent] = []
        self.prefs: list[dict[str, int]] = []
        self.limits_mode: list[bool] = []
        self.rechecked: list[str] = []
        self.logged_in = False

    def auth_log_in(self) -> None:
        self.logged_in = True

    def transfer_info(self) -> dict[str, Any]:
        return QbtTransferInfo(up_info_speed=self.up_info_speed).model_dump()

    def app_set_preferences(self, prefs: dict[str, int]) -> None:
        self.prefs.append(prefs)

    def transfer_set_speed_limits_mode(self, enabled: bool) -> None:
        self.limits_mode.append(enabled)

    def torrents_info(self, status_filter: str = "") -> list[QbtTorrent]:
        return self.torrents

    def torrents_recheck(self, torrent_hashes: list[str]) -> None:
        self.rechecked = list(torrent_hashes)


class FakeHaClient:
    """homeassistant_api.AsyncClient stand-in; `states` maps entity_id to its state."""

    states: ClassVar[dict[str, str]] = {}

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get_state(self, *, entity_id: str) -> HaState:
        return HaState(entity_id=entity_id, state=self.states.get(entity_id, "not_home"))


def as_client_session(session: FakeSession) -> aiohttp.ClientSession:
    """Hand a FakeSession to code annotated for aiohttp.ClientSession."""
    return cast("aiohttp.ClientSession", session)
