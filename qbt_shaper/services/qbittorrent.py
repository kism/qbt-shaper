"""qBittorrent API client."""

import asyncio
from typing import TYPE_CHECKING

import qbittorrentapi

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    from qbt_shaper.config import QbittorrentConfig, QbittorrentSpeedConfig
else:
    QbittorrentConfig = object
    QbittorrentSpeedConfig = object

logger = get_logger(__name__)


class QbittorrentClient:
    """Client for the qBittorrent WebUI API.

    Uses the synchronous qbittorrentapi library wrapped in asyncio.to_thread
    so it plays nicely with the async event loop.
    """

    def __init__(self, config: QbittorrentConfig, speed: QbittorrentSpeedConfig) -> None:
        self._speed = speed
        self._client = qbittorrentapi.Client(
            host=config.url,
            username=config.username,
            password=config.password,
        )
        self._applied_global: tuple[int, int] | None = None
        self._applied_alt: tuple[int, int] | None = None
        self._applied_limit_enabled: bool | None = None

    async def login(self) -> None:
        """Authenticate with the qBittorrent WebUI."""
        await asyncio.to_thread(self._client.auth_log_in)
        logger.info("Logged in to qBittorrent at %s", self._client.host)

    async def get_upload_speed_bytes(self) -> int:
        """Return the current upload speed in bytes/s."""
        info = await asyncio.to_thread(self._client.transfer_info)
        speed = info["up_info_speed"]
        return speed if isinstance(speed, int) else 0

    def base_limit_bytes(self, presence: str) -> tuple[int, int]:
        """Return (dl_bytes, ul_bytes) for the given presence state ('present' or 'vacant')."""
        if presence == "vacant":
            dl = self._kbps_percent_to_bytes(self._speed.dl_max_kbps, self._speed.dl_vacant_percent)
            ul = self._kbps_percent_to_bytes(self._speed.ul_max_kbps, self._speed.ul_vacant_percent)
        else:
            dl = self._kbps_percent_to_bytes(self._speed.dl_max_kbps, self._speed.dl_present_percent)
            ul = self._kbps_percent_to_bytes(self._speed.ul_max_kbps, self._speed.ul_present_percent)
        return dl, ul

    @staticmethod
    def _kbps_percent_to_bytes(max_kbps: int, percent: int) -> int:
        """Convert a percentage of a kbps bandwidth cap to bytes/s."""
        return max_kbps * percent * 125 // 100

    async def set_alt_speed_limits(self, dl_kib: int, ul_kib: int) -> None:
        """Set the alternative (throttled) speed limits in KiB/s. 0 means unlimited."""
        dl_bytes = dl_kib * 1024
        ul_bytes = ul_kib * 1024
        if self._applied_alt == (dl_bytes, ul_bytes):
            return
        await asyncio.to_thread(
            self._client.app_set_preferences,
            {"alt_dl_limit": dl_bytes, "alt_up_limit": ul_bytes},
        )
        self._applied_alt = (dl_bytes, ul_bytes)
        logger.info(
            "Set alt speed limits (streaming mode) on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            self._client.host,
            dl_kib,
            ul_kib,
        )

    async def apply_streaming_limits(self) -> None:
        """Apply the configured streaming speed limits as the alternative speed limits."""
        dl = self._kbps_percent_to_bytes(self._speed.dl_max_kbps, self._speed.dl_streaming_percent)
        ul = self._kbps_percent_to_bytes(self._speed.ul_max_kbps, self._speed.ul_streaming_percent)
        await self.set_alt_speed_limits(dl_kib=dl // 1024, ul_kib=ul // 1024)

    async def _apply_global_limits(self, description: str, dl_bytes: int, ul_bytes: int) -> None:
        if self._applied_global == (dl_bytes, ul_bytes):
            return
        await asyncio.to_thread(
            self._client.app_set_preferences,
            {"dl_limit": dl_bytes, "up_limit": ul_bytes},
        )
        self._applied_global = (dl_bytes, ul_bytes)
        logger.info(
            "Set %s speed limits on qBittorrent at %s: dl=%d KiB/s ul=%d KiB/s",
            description,
            self._client.host,
            dl_bytes // 1024,
            ul_bytes // 1024,
        )

    async def apply_present_limits(self) -> None:
        """Apply the configured present (someone home) speed limits."""
        await self._apply_global_limits(
            "present",
            self._kbps_percent_to_bytes(self._speed.dl_max_kbps, self._speed.dl_present_percent),
            self._kbps_percent_to_bytes(self._speed.ul_max_kbps, self._speed.ul_present_percent),
        )

    async def apply_vacant_limits(self) -> None:
        """Apply the configured vacant (nobody home) speed limits."""
        await self._apply_global_limits(
            "vacant",
            self._kbps_percent_to_bytes(self._speed.dl_max_kbps, self._speed.dl_vacant_percent),
            self._kbps_percent_to_bytes(self._speed.ul_max_kbps, self._speed.ul_vacant_percent),
        )

    async def set_speed_limit_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the global alternative speed limit mode.

        :param enabled: True to enable speed limiting, False to disable.
        """
        if self._applied_limit_enabled == enabled:
            return
        await asyncio.to_thread(self._client.transfer_set_speed_limits_mode, enabled)
        self._applied_limit_enabled = enabled
        state = "enabled" if enabled else "disabled"
        logger.info("Speed limit %s on qBittorrent at %s", state, self._client.host)
