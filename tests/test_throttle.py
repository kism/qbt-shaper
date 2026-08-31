"""Priority throttler tests."""

import asyncio

from qbt_shaper.config import QbittorrentSpeedConfig
from qbt_shaper.throttle import PriorityThrottler

# 1000 kbps == 125000 bytes/s, and 100% of that is the base limit for both tests.
SPEED = QbittorrentSpeedConfig(dl_max_kbps=1000, ul_max_kbps=1000, dl_present_percent=100, ul_present_percent=100)


def test_apply_reduces_lower_priority(qbt):
    high = qbt(SPEED, priority=1)
    low = qbt(SPEED, priority=2)
    high._client.up_info_speed = 62500  # half the 125000 bytes/s cap

    asyncio.run(PriorityThrottler([high, low], SPEED).apply("present"))

    assert high._client.prefs[-1]["up_limit"] == 125000
    assert low._client.prefs[-1]["up_limit"] == 56249  # 55% reduction (half the cap x1.1 penalty), float-truncated


def test_apply_does_not_throttle_peers(qbt):
    peers = [qbt(SPEED, priority=1), qbt(SPEED, priority=1)]
    peers[0]._client.up_info_speed = 125000  # saturating the cap

    asyncio.run(PriorityThrottler(peers, SPEED).apply("present"))

    assert [p._client.prefs[-1]["up_limit"] for p in peers] == [125000, 125000]
