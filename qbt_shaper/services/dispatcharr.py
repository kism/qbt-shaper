"""Dispatcharr API client."""

from typing import TYPE_CHECKING, Any
from http import HTTPStatus

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from qbt_shaper.config import DispatcharrConfig

logger = get_logger(__name__)

_TOKEN_PATH = "/api/accounts/token/"
_TS_STATUS_PATH = "/proxy/ts/status"


class DispatcharrClient:
    """Async client for the Dispatcharr API.

    Authenticates via JWT (POST /api/accounts/token/) and checks active
    stream counts via GET /proxy/ts/status.
    """

    def __init__(self, config: DispatcharrConfig, session: aiohttp.ClientSession) -> None:
        self._config = config
        self._session = session
        self._token: str | None = None

    def _url(self, path: str) -> str:
        return self._config.url.rstrip("/") + path

    def _auth_headers(self) -> dict[str, str]:
        if self._token is None:
            msg = "Not logged in — call login() first"
            raise RuntimeError(msg)
        return {"Authorization": f"Bearer {self._token}"}

    async def login(self) -> None:
        """Obtain a JWT access token using the configured credentials."""
        payload = {
            "username": self._config.username,
            "password": self._config.password,
        }
        async with self._session.post(self._url(_TOKEN_PATH), json=payload) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json()
        self._token = data["access"]
        logger.info("Logged in to Dispatcharr at %s", self._config.url)

    async def has_active_streams(self) -> bool:
        """Return True if any channel is currently active.

        Fetches GET /proxy/ts/status and checks the top-level ``count`` field.
        Re-authenticates once if the token has expired (HTTP 401).
        """
        if self._token is None:
            await self.login()

        async with self._session.get(self._url(_TS_STATUS_PATH), headers=self._auth_headers()) as resp:
            if resp.status == HTTPStatus.UNAUTHORIZED:
                logger.debug("Dispatcharr token expired, re-authenticating")
                self._token = None
                await self.login()
            else:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                count: int = data.get("count", 0)
                logger.debug("Dispatcharr %s: %d active channel(s)", self._config.url, count)
                return count > 0

        async with self._session.get(self._url(_TS_STATUS_PATH), headers=self._auth_headers()) as resp:
            resp.raise_for_status()
            data = await resp.json()

        count = data.get("count", 0)
        logger.debug("Dispatcharr %s: %d active channel(s)", self._config.url, count)
        return count > 0
