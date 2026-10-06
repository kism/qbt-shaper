"""Main loop tests."""

import asyncio
import logging
from typing import Any, cast

import pytest

from qbt_shaper import loop
from qbt_shaper.config import AppConfig, BedtimeConfig, HomeAssistantConfig, JellyfinConfig
from qbt_shaper.services.homeassistant import HomeAssistantClient
from qbt_shaper.services.jellyfin import JellyfinClient
from qbt_shaper.utils.backoff import BackoffActiveError
from tests.mocks import FakeHaClient, FakeResponse, FakeSession, JellyfinAuth, JellyfinSession, as_client_session


def test_check_active_streams():
    session = FakeSession(FakeResponse(JellyfinAuth()), FakeResponse([JellyfinSession(NowPlayingItem={"Name": "x"})]))
    client = JellyfinClient(JellyfinConfig(url="http://jf", username="u", password="p"), as_client_session(session))

    assert asyncio.run(loop._check_active_streams([client], [])) is True


def test_determine_presence(monkeypatch):
    monkeypatch.setattr("qbt_shaper.services.homeassistant.AsyncClient", FakeHaClient)
    unconfigured = HomeAssistantClient(HomeAssistantConfig())
    configured = HomeAssistantClient(
        HomeAssistantConfig(url="http://ha", token="t", presence_entities=["device_tracker.phone"]),
    )

    assert asyncio.run(loop._determine_presence(unconfigured)) == "present"
    assert asyncio.run(loop._determine_presence(configured)) == "vacant"


@pytest.fixture
def run_loop(monkeypatch):
    """Run `run_loop` for a fixed number of iterations without sleeping."""

    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(loop.asyncio, "sleep", no_sleep)

    def _run(config: AppConfig, iterations: int = 1) -> None:
        monkeypatch.setattr(loop, "LOOP_ITERATIONS", iterations)
        asyncio.run(loop.run_loop(config))

    return _run


class _FailingClient:
    """Stands in for any service client; every call raises `exc`."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def _raise(self, **_kwargs):
        raise self.exc

    has_active_streams = set_speed_limit_enabled = apply_streaming_limits = recheck_errored = _raise


def test_helpers_tolerate_failures(caplog):
    clients = cast("list[Any]", [_FailingClient(BackoffActiveError()), _FailingClient(RuntimeError())])

    async def run_all():
        assert await loop._check_active_streams(clients, []) is False
        await loop._apply_speed_limit(clients, limit=True)
        await loop._apply_streaming_limits(clients)
        await loop._recheck_errored_torrents(clients)

    asyncio.run(run_all())

    for msg in ("Stream check failed", "Failed to set speed limit", "Failed to set streaming", "recheck failed"):
        assert msg in caplog.text


def test_run_loop_single_pass(run_loop, caplog):
    caplog.set_level(logging.INFO)

    run_loop(AppConfig())

    assert "streaming=false, someone_home=true, bed_time=false" in caplog.text


def test_run_loop_stream_cooldown_and_bedtime(run_loop, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    streaming = iter([True, False])

    async def fake_check(*_args):
        return next(streaming)

    monkeypatch.setattr(loop, "_check_active_streams", fake_check)
    monkeypatch.setattr(BedtimeConfig, "is_active", lambda _self: True)

    run_loop(AppConfig(), iterations=2)

    assert "streaming=true, someone_home=true, bed_time=true" in caplog.text
    assert "Stream cooldown active" in caplog.text
    assert "Bedtime active" in caplog.text


def test_run_loop_survives_unreachable_services(run_loop, monkeypatch, caplog):
    config = AppConfig.model_validate(
        {"qbittorrent_instances": [{"url": "http://qbt.invalid", "username": "u", "password": "p"}]}
    )

    async def unreachable(*_args, **_kwargs):
        raise ConnectionError

    async def boom(*_args, **_kwargs):
        raise RuntimeError

    monkeypatch.setattr(loop.QbittorrentClient, "apply_streaming_limits", unreachable)
    monkeypatch.setattr(loop, "_check_active_streams", boom)

    run_loop(config, iterations=2)

    assert "Failed to set streaming limits" in caplog.text
    assert "Unexpected error in main loop" in caplog.text
