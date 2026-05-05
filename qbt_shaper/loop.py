"""Main application loop."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiohttp

from .services.dispatcharr import DispatcharrClient
from .services.jellyfin import JellyfinClient
from .services.qbittorrent import QbittorrentClient
from .utils.logger import get_logger

if TYPE_CHECKING:
    from .config import AppConfig

LOOP_INTERVAL_SECONDS = 15

logger = get_logger(__name__)


async def _check_active_streams(
    jellyfin_clients: list[JellyfinClient],
    dispatcharr_clients: list[DispatcharrClient],
) -> bool:
    """Return True if any Jellyfin or Dispatcharr instance reports active streams."""
    checks = [
        *[client.has_active_streams() for client in jellyfin_clients],
        *[client.has_active_streams() for client in dispatcharr_clients],
    ]
    results = await asyncio.gather(*checks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Stream check failed: %s", result)
        elif result is True:
            return True
    return False


async def _apply_speed_limit(
    qbt_clients: list[QbittorrentClient],
    *,
    limit: bool,
) -> None:
    """Enable or disable speed limiting on all configured qBittorrent instances."""
    for client in qbt_clients:
        try:
            await client.set_speed_limit_enabled(enabled=limit)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to set speed limit on qBittorrent instance", exc_info=True)


async def run_loop(config: AppConfig) -> None:
    """Run the main monitoring and control loop."""
    async with aiohttp.ClientSession() as session:
        jellyfin_clients = [JellyfinClient(cfg, session) for cfg in config.jellyfin_instances]
        dispatcharr_clients = [DispatcharrClient(cfg, session) for cfg in config.dispatcharr_instances]
        qbt_clients = [QbittorrentClient(cfg) for cfg in config.qbittorrent_instances]

        logger.info(
            "Monitoring %d Jellyfin, %d Dispatcharr, %d qBittorrent instance(s)",
            len(jellyfin_clients),
            len(dispatcharr_clients),
            len(qbt_clients),
        )

        while True:
            active = await _check_active_streams(jellyfin_clients, dispatcharr_clients)
            await _apply_speed_limit(qbt_clients, limit=active)
            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
