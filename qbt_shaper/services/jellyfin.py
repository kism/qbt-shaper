"""Jellyfin API client."""

from typing import TYPE_CHECKING, Any

from qbt_shaper.constants import PROGRAM_NAME, PROGRAM_VERSION
from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from qbt_shaper.config import JellyfinConfig

logger = get_logger(__name__)

_AUTH_PATH = "/Users/AuthenticateByName"
_SESSIONS_PATH = "/Sessions"


class JellyfinClient:
    """Async client for the Jellyfin API."""

    def __init__(self, config: JellyfinConfig, session: aiohttp.ClientSession) -> None:
        self._config = config
        self._session = session
        self._token: str | None = None

    def _url(self, path: str) -> str:
        return self._config.url.rstrip("/") + path

    def _mediabrowser_header(self, *, token: str | None = None) -> dict[str, str]:
        parts = [
            f'Client="{PROGRAM_NAME}"',
            f'Device="{PROGRAM_NAME}"',
            f'DeviceId="{PROGRAM_NAME}"',
            f'Version="{PROGRAM_VERSION}"',
        ]
        if token is not None:
            parts.append(f'Token="{token}"')
        return {"Authorization": "MediaBrowser " + ", ".join(parts)}

    async def login(self) -> None:
        """Obtain an access token using the configured credentials."""
        payload = {
            "Username": self._config.username,
            "Pw": self._config.password,
        }
        async with self._session.post(
            self._url(_AUTH_PATH),
            json=payload,
            headers=self._mediabrowser_header(),
        ) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json()
        self._token = data["AccessToken"]
        logger.info("Logged in to Jellyfin at %s", self._config.url)

    async def has_active_streams(self) -> bool:
        """Return True if any session currently has a NowPlayingItem."""
        if self._token is None:
            await self.login()

        async with self._session.get(
            self._url(_SESSIONS_PATH),
            headers=self._mediabrowser_header(token=self._token),
        ) as resp:
            resp.raise_for_status()
            sessions: list[dict[str, Any]] = await resp.json()

        active = sum(1 for s in sessions if s.get("NowPlayingItem") is not None)
        logger.debug("Jellyfin %s: %d active stream(s)", self._config.url, active)
        return active > 0
