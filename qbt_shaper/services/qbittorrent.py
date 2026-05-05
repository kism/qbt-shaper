"""qBittorrent API client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import qbittorrentapi

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    from qbt_shaper.config import QbittorrentConfig

logger = get_logger(__name__)


class QbittorrentClient:
    """Client for the qBittorrent WebUI API.

    Uses the synchronous qbittorrentapi library wrapped in asyncio.to_thread
    so it plays nicely with the async event loop.
    """

    def __init__(self, config: QbittorrentConfig) -> None:
        self._client = qbittorrentapi.Client(
            host=config.url,
            username=config.username,
            password=config.password.get_secret_value(),
        )

    async def login(self) -> None:
        """Authenticate with the qBittorrent WebUI."""
        await asyncio.to_thread(self._client.auth_log_in)
        logger.info("Logged in to qBittorrent at %s", self._client.host)

    async def set_speed_limit_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the global alternative speed limit mode.

        :param enabled: True to enable speed limiting, False to disable.
        """
        await asyncio.to_thread(self._client.transfer_set_speed_limits_mode, enabled)
        state = "enabled" if enabled else "disabled"
        logger.info("Speed limit %s on qBittorrent at %s", state, self._client.host)
