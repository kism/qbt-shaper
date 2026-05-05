"""Dispatcharr API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from qbt_shaper.config import DispatcharrConfig

logger = get_logger(__name__)

_TOKEN_PATH = "/api/accounts/token/"
_M3U_ACCOUNTS_PATH = "/api/m3u/accounts/"


class DispatcharrClient:
    """Async client for the Dispatcharr API.

    Authenticates via JWT (POST /api/accounts/token/) and checks active
    viewer counts across all M3U account profiles.
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
            "password": self._config.password.get_secret_value(),
        }
        async with self._session.post(self._url(_TOKEN_PATH), json=payload) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json()
        self._token = data["access"]
        logger.info("Logged in to Dispatcharr at %s", self._config.url)

    async def has_active_streams(self) -> bool:
        """Return True if any M3U account profile currently has viewers.

        Fetches GET /api/m3u/accounts/ and sums current_viewers across all
        profiles in all accounts.
        """
        async with self._session.get(self._url(_M3U_ACCOUNTS_PATH), headers=self._auth_headers()) as resp:
            resp.raise_for_status()
            accounts: list[dict[str, Any]] = await resp.json()

        total_viewers = sum(
            profile.get("current_viewers", 0)
            for account in accounts
            for profile in account.get("profiles", [])
        )

        logger.debug("Dispatcharr %s: %d active viewer(s)", self._config.url, total_viewers)
        return total_viewers > 0
