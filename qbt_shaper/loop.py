"""Main application loop."""

import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp

from .services.dispatcharr import DispatcharrClient
from .services.homeassistant import HomeAssistantClient
from .services.jellyfin import JellyfinClient
from .services.qbittorrent import QbittorrentClient
from .utils.logger import get_logger

if TYPE_CHECKING:
    from .config import AppConfig

LOOP_INTERVAL_SECONDS = 15
PRESENCE_CHECK_INTERVAL_SECONDS = 60

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


async def _apply_presence_limits(
    qbt_clients: list[QbittorrentClient],
    ha_client: HomeAssistantClient,
) -> None:
    """Apply vacant or present speed limits based on Home Assistant presence."""
    if ha_client.is_configured():
        anyone_home = await ha_client.any_entity_home()
        apply = QbittorrentClient.apply_present_limits if anyone_home else QbittorrentClient.apply_vacant_limits
        state = "present" if anyone_home else "vacant"
        logger.debug("Presence state: %s", state)
    else:
        apply = QbittorrentClient.apply_present_limits
        logger.debug("Home Assistant not configured, applying present limits as default")

    for client in qbt_clients:
        try:
            await apply(client)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to apply presence limits on qBittorrent instance", exc_info=True)


async def run_loop(config: AppConfig) -> None:
    """Run the main monitoring and control loop."""
    async with aiohttp.ClientSession() as session:
        jellyfin_clients = [JellyfinClient(cfg, session) for cfg in config.jellyfin_instances]
        dispatcharr_clients = [DispatcharrClient(cfg, session) for cfg in config.dispatcharr_instances]
        qbt_clients = [QbittorrentClient(cfg) for cfg in config.qbittorrent_instances]
        ha_client = HomeAssistantClient(config.home_assistant)

        logger.info(
            "Monitoring %d Jellyfin, %d Dispatcharr, %d qBittorrent instance(s)",
            len(jellyfin_clients),
            len(dispatcharr_clients),
            len(qbt_clients),
        )

        for client in qbt_clients:
            await client.login()
            await client.apply_streaming_limits()
            await client.apply_present_limits()

        last_presence_check = time.monotonic() - PRESENCE_CHECK_INTERVAL_SECONDS

        while True:
            now = time.monotonic()

            active = await _check_active_streams(jellyfin_clients, dispatcharr_clients)
            await _apply_speed_limit(qbt_clients, limit=active)

            if now - last_presence_check >= PRESENCE_CHECK_INTERVAL_SECONDS:
                await _apply_presence_limits(qbt_clients, ha_client)
                last_presence_check = now

            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
