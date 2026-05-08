"""Priority-based upload throttling for qBittorrent instances."""

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING

from .services.qbittorrent import QbittorrentClient
from .utils.logger import get_logger

if TYPE_CHECKING:
    from .config import QbittorrentSpeedConfig

MAX_PRIORITY_REDUCTION = 0.8
SPEED_HISTORY_SIZE = 10
_MIN_DISPLAY_REDUCTION = 0.005  # reductions below this round to 0% in format strings

logger = get_logger(__name__)


class PriorityThrottler:
    """Applies per-instance global limits with priority-based upload throttling.

    Instances are grouped by their ``priority`` value (lower = higher priority).
    For each group the combined upload speed of all strictly higher-priority
    groups is measured and used to proportionally reduce that group's upload
    limit, capped at MAX_PRIORITY_REDUCTION.  Instances within the same
    priority group are treated as peers and do not throttle each other.
    """

    def __init__(self, clients: list[QbittorrentClient], speed: "QbittorrentSpeedConfig") -> None:
        self._clients = clients
        self._ul_max_bytes = speed.ul_max_kbps * 125  # kbps → bytes/s

        # Per-client upload speed history (bytes/s), capped at SPEED_HISTORY_SIZE readings.
        self._speed_history: list[deque[int]] = [deque(maxlen=SPEED_HISTORY_SIZE) for _ in clients]

        # Group clients (with their original index) by priority level.
        self._groups: dict[int, list[tuple[int, QbittorrentClient]]] = {}
        for i, client in enumerate(clients):
            self._groups.setdefault(client.priority, []).append((i, client))
        self._sorted_levels = sorted(self._groups.keys())

    async def apply(self, presence: str) -> None:
        """Apply throttled global limits to all clients for the given presence state."""
        upload_speeds: list[int] = []
        if self._ul_max_bytes > 0 and len(self._sorted_levels) > 1:
            results = await asyncio.gather(
                *[c.get_upload_speed_bytes() for c in self._clients],
                return_exceptions=True,
            )
            for j, r in enumerate(results):
                sample = r if isinstance(r, int) else 0
                self._speed_history[j].append(sample)
                upload_speeds.append(max(self._speed_history[j]))
            logger.debug(
                "Priority throttle: peak upload speeds (KiB/s): %s",
                ", ".join(f"#{j}={s // 1024}" for j, s in enumerate(upload_speeds)),
            )

        cumulative_upload = 0  # combined upload of all higher-priority groups so far
        for level in self._sorted_levels:
            group = self._groups[level]
            if upload_speeds and cumulative_upload > 0:
                reduction = min(cumulative_upload / self._ul_max_bytes, MAX_PRIORITY_REDUCTION)
                logger.log(
                    logging.DEBUG if reduction > 0 else logging.INFO,
                    "Priority throttle level %d: higher-priority upload=%d KiB/s of %d KiB/s max → %.0f%% reduction",
                    level,
                    cumulative_upload // 1024,
                    self._ul_max_bytes // 1024,
                    reduction * 100,
                )
            else:
                reduction = 0.0

            # Accumulate this group's upload before processing the next level.
            if upload_speeds:
                cumulative_upload += sum(upload_speeds[i] for i, _ in group)

            for _, client in group:
                base_dl, base_ul = client.base_limit_bytes(presence)
                throttled_ul = int(base_ul * (1 - reduction))
                description = (
                    f"priority-throttled ({reduction:.0%} reduction)"
                    if reduction >= _MIN_DISPLAY_REDUCTION
                    else presence
                )
                try:
                    await client._apply_global_limits(description, base_dl, throttled_ul)  # noqa: SLF001
                except Exception:  # noqa: BLE001
                    logger.warning("Failed to apply limits on qBittorrent instance", exc_info=True)
