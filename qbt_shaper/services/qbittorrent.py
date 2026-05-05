"""qBittorrent API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from ..config import QbittorrentConfig

logger = get_logger(__name__)


class QbittorrentClient:
    """Async client for the qBittorrent WebUI API."""

    def __init__(self, config: QbittorrentConfig, session: aiohttp.ClientSession) -> None:
        self._config = config
        self._session = session

    async def set_speed_limit_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the global speed limit mode."""
        raise NotImplementedError
