"""qBittorrent client tests."""

import asyncio

from qbt_shaper.config import QbittorrentSpeedConfig
from tests.mocks import QbtTorrent

SPEED = QbittorrentSpeedConfig(
    dl_max_kbps=1000,
    ul_max_kbps=1000,
    dl_present_percent=50,
    ul_present_percent=20,
    dl_vacant_percent=100,
    ul_vacant_percent=100,
    dl_streaming_percent=10,
    ul_streaming_percent=10,
)


def test_base_limit_bytes(qbt):
    client = qbt(SPEED)

    assert client.base_limit_bytes("present") == (62500, 25000)
    assert client.base_limit_bytes("vacant") == (125000, 125000)


def test_apply_global_limits_skips_redundant_calls(qbt):
    client = qbt(SPEED)

    asyncio.run(client._apply_global_limits("present", 62500, 25000))
    asyncio.run(client._apply_global_limits("present", 62500, 25000))

    assert client._client.prefs == [{"dl_limit": 62500, "up_limit": 25000}]


def test_apply_streaming_limits(qbt):
    client = qbt(SPEED)

    asyncio.run(client.apply_streaming_limits())

    assert client._client.prefs == [{"alt_dl_limit": 12288, "alt_up_limit": 12288}]  # 12500 bytes/s, rounded to KiB


def test_set_speed_limit_enabled_skips_redundant_calls(qbt):
    client = qbt(SPEED)

    asyncio.run(client.set_speed_limit_enabled(enabled=True))
    asyncio.run(client.set_speed_limit_enabled(enabled=True))
    asyncio.run(client.set_speed_limit_enabled(enabled=False))

    assert client._client.limits_mode == [True, False]


def test_recheck_errored(qbt):
    client = qbt(SPEED, force_recheck_errored=True)
    client._client.torrents = [QbtTorrent(hash="abc123")]
    disabled = qbt(SPEED)
    disabled._client.torrents = [QbtTorrent(hash="def456")]

    asyncio.run(client.recheck_errored())
    asyncio.run(disabled.recheck_errored())

    assert client._client.rechecked == ["abc123"]
    assert disabled._client.rechecked == []
