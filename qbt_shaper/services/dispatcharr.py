"""Dispatcharr API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.logger import get_logger

if TYPE_CHECKING:
    import aiohttp

    from ..config import DispatcharrConfig

logger = get_logger(__name__)


class DispatcharrClient:
    """Async client for the Dispatcharr API."""

    def __init__(self, config: DispatcharrConfig, session: aiohttp.ClientSession) -> None:
        self._config = config
        self._session = session

    async def has_active_streams(self) -> bool:
        """Return True if any users are currently streaming."""
        raise NotImplementedError
