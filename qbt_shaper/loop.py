"""Main application loop."""

import asyncio
import time

import aiohttp

from .config import AppConfig
from .services.dispatcharr import DispatcharrClient
from .services.homeassistant import HomeAssistantClient
from .services.jellyfin import JellyfinClient
from .services.qbittorrent import QbittorrentClient
from .throttle import PriorityThrottler
from .utils.logger import get_logger

LOOP_INTERVAL_SECONDS = 15
PRESENCE_CHECK_INTERVAL_SECONDS = 60
STREAM_COOLDOWN_SECONDS = 600  # 10 minutes

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


async def _determine_presence(ha_client: HomeAssistantClient) -> str:
    """Return 'present' or 'vacant' based on Home Assistant presence state."""
    if not ha_client.is_configured():
        logger.debug("Home Assistant not configured, defaulting to present")
        return "present"
    anyone_home = await ha_client.any_entity_home()
    state = "present" if anyone_home else "vacant"
    logger.debug("Presence state: %s", state)
    return state


async def run_loop(config: AppConfig) -> None:
    """Run the main monitoring and control loop."""
    async with aiohttp.ClientSession() as session:
        jellyfin_clients = [JellyfinClient(cfg, session) for cfg in config.jellyfin_instances]
        dispatcharr_clients = [DispatcharrClient(cfg, session) for cfg in config.dispatcharr_instances]
        qbt_clients = [QbittorrentClient(cfg, config.qbittorrent_speed) for cfg in config.qbittorrent_instances]
        ha_client = HomeAssistantClient(config.home_assistant)

        logger.info(
            "Monitoring %d Jellyfin, %d Dispatcharr, %d qBittorrent instance(s)",
            len(jellyfin_clients),
            len(dispatcharr_clients),
            len(qbt_clients),
        )

        throttler = PriorityThrottler(qbt_clients, config.qbittorrent_speed)

        for client in qbt_clients:
            await client.login()
            await client.apply_streaming_limits()

        current_presence = "present"
        last_presence_check = time.monotonic() - PRESENCE_CHECK_INTERVAL_SECONDS
        last_stream_active: float | None = None

        while True:
            now = time.monotonic()

            active = await _check_active_streams(jellyfin_clients, dispatcharr_clients)
            if active:
                last_stream_active = now

            if not active and last_stream_active is not None:
                elapsed = now - last_stream_active
                in_cooldown = elapsed < STREAM_COOLDOWN_SECONDS
                if in_cooldown:
                    remaining = int(STREAM_COOLDOWN_SECONDS - elapsed)
                    logger.debug("Stream cooldown active, %ds remaining before releasing throttle", remaining)
            else:
                in_cooldown = False

            await _apply_speed_limit(qbt_clients, limit=active or in_cooldown)

            if now - last_presence_check >= PRESENCE_CHECK_INTERVAL_SECONDS:
                current_presence = await _determine_presence(ha_client)
                last_presence_check = now

            effective_presence = current_presence
            if config.bedtime.is_active():
                effective_presence = "vacant"
                logger.debug("Bedtime active, overriding presence '%s' → 'vacant'", current_presence)

            await throttler.apply(effective_presence)

            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
