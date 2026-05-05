"""Jellyfin API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from qbt_shaper.config import JellyfinConfig

logger = get_logger(__name__)


class JellyfinClient:
    """Async client for the Jellyfin API."""

    def __init__(self, config: JellyfinConfig, session: aiohttp.ClientSession) -> None:
        self._config = config
        self._session = session

    async def has_active_streams(self) -> bool:
        """Return True if any users are currently streaming."""
        raise NotImplementedError
