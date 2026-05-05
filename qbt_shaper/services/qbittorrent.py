"""qBittorrent API client."""

import asyncio
from typing import TYPE_CHECKING

import qbittorrentapi

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    from qbt_shaper.config import QbittorrentConfig
else:
    QbittorrentConfig = object

logger = get_logger(__name__)


class QbittorrentClient:
    """Client for the qBittorrent WebUI API.

    Uses the synchronous qbittorrentapi library wrapped in asyncio.to_thread
    so it plays nicely with the async event loop.
    """

    def __init__(self, config: QbittorrentConfig) -> None:
        self._config = config
        self._client = qbittorrentapi.Client(
            host=config.url,
            username=config.username,
            password=config.password,
        )

    async def login(self) -> None:
        """Authenticate with the qBittorrent WebUI."""
        await asyncio.to_thread(self._client.auth_log_in)
        logger.info("Logged in to qBittorrent at %s", self._client.host)

    async def set_alt_speed_limits(self, dl_kib: int, ul_kib: int) -> None:
        """Set the alternative (throttled) speed limits in KiB/s. 0 means unlimited."""
        dl_field = "alt_dl_limit"
        ul_field = "alt_up_limit"
        # Convert dl_ for god knows why
        dl_kib = dl_kib * 1024
        ul_kib = ul_kib * 1024

        await asyncio.to_thread(
            self._client.app_set_preferences,
            {dl_field: dl_kib, ul_field: ul_kib},
        )
        logger.info(
            "Set alt speed limits on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            self._client.host,
            dl_kib,
            ul_kib,
        )
        current_settings = self._client.app_preferences()

        logger.warning(
            "Current alt speed limits on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            self._client.host,
            current_settings[dl_field],
            current_settings[ul_field],
        )

    async def apply_streaming_limits(self) -> None:
        """Apply the configured streaming speed limits as the alternative speed limits."""
        limits = self._config.speed_limits.streaming
        await self.set_alt_speed_limits(dl_kib=limits.dl, ul_kib=limits.ul)

    async def apply_present_limits(self) -> None:
        """Apply the configured present (someone home) speed limits."""
        limits = self._config.speed_limits.present
        await asyncio.to_thread(
            self._client.app_set_preferences,
            {"dl_limit": limits.dl * 1024, "up_limit": limits.ul * 1024},
        )
        logger.info(
            "Set present speed limits on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            self._client.host,
            limits.dl,
            limits.ul,
        )

    async def apply_vacant_limits(self) -> None:
        """Apply the configured vacant (nobody home) speed limits."""
        limits = self._config.speed_limits.vacant
        await asyncio.to_thread(
            self._client.app_set_preferences,
            {"dl_limit": limits.dl * 1024, "up_limit": limits.ul * 1024},
        )
        logger.info(
            "Set vacant speed limits on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            self._client.host,
            limits.dl,
            limits.ul,
        )

    async def set_speed_limit_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the global alternative speed limit mode.

        :param enabled: True to enable speed limiting, False to disable.
        """
        await asyncio.to_thread(self._client.transfer_set_speed_limits_mode, enabled)
        state = "enabled" if enabled else "disabled"
        logger.info("Speed limit %s on qBittorrent at %s", state, self._client.host)
