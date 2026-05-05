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
    from .config import AppConfig, QbittorrentSpeedConfig

LOOP_INTERVAL_SECONDS = 15
PRESENCE_CHECK_INTERVAL_SECONDS = 60
MAX_PRIORITY_REDUCTION = 0.8

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


async def _apply_priority_throttling(
    qbt_clients: list[QbittorrentClient],
    speed: QbittorrentSpeedConfig,
    presence: str,
) -> None:
    """Apply per-instance global limits with priority-based upload throttling.

    Instances are ordered by priority (index 0 = highest).  For each instance
    the combined upload speed of all higher-priority instances is measured and
    used to proportionally reduce that instance's upload limit, capped at
    MAX_PRIORITY_REDUCTION.
    """
    ul_max_bytes = speed.ul_max_kbps * 125  # kbps → bytes/s

    upload_speeds: list[int] = []
    if ul_max_bytes > 0 and len(qbt_clients) > 1:
        results = await asyncio.gather(
            *[c.get_upload_speed_bytes() for c in qbt_clients],
            return_exceptions=True,
        )
        for r in results:
            upload_speeds.append(r if isinstance(r, int) else 0)
        logger.debug(
            "Priority throttle: upload speeds (KiB/s): %s",
            ", ".join(f"#{j}={s // 1024}" for j, s in enumerate(upload_speeds)),
        )

    for i, client in enumerate(qbt_clients):
        base_dl, base_ul = client.base_limit_bytes(presence)
        if upload_speeds and i > 0:
            combined_higher = sum(upload_speeds[:i])
            reduction = min(combined_higher / ul_max_bytes, MAX_PRIORITY_REDUCTION)
            logger.debug(
                "Priority throttle #%d: combined higher-priority upload=%d KiB/s of %d KiB/s max → %.0f%% reduction",
                i,
                combined_higher // 1024,
                ul_max_bytes // 1024,
                reduction * 100,
            )
        else:
            reduction = 0.0
        throttled_ul = int(base_ul * (1 - reduction))
        description = f"priority-throttled ({reduction:.0%} reduction)" if reduction else presence
        try:
            await client._apply_global_limits(description, base_dl, throttled_ul)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            logger.warning("Failed to apply limits on qBittorrent instance", exc_info=True)


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

        for client in qbt_clients:
            await client.login()
            await client.apply_streaming_limits()

        current_presence = "present"
        last_presence_check = time.monotonic() - PRESENCE_CHECK_INTERVAL_SECONDS

        while True:
            now = time.monotonic()

            active = await _check_active_streams(jellyfin_clients, dispatcharr_clients)
            await _apply_speed_limit(qbt_clients, limit=active)

            if now - last_presence_check >= PRESENCE_CHECK_INTERVAL_SECONDS:
                current_presence = await _determine_presence(ha_client)
                last_presence_check = now

            await _apply_priority_throttling(qbt_clients, config.qbittorrent_speed, current_presence)

            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
