"""Main loop tests."""

import asyncio
import logging

import pytest

from qbt_shaper import loop
from qbt_shaper.config import AppConfig, HomeAssistantConfig, JellyfinConfig
from qbt_shaper.services.homeassistant import HomeAssistantClient
from qbt_shaper.services.jellyfin import JellyfinClient
from tests.mocks import FakeHaClient, FakeResponse, FakeSession, JellyfinAuth, JellyfinSession, as_client_session


class _StopLoopError(Exception):
    """Breaks out of the otherwise infinite loop."""


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


def test_run_loop_single_pass(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    async def fake_sleep(delay):
        if delay == loop.LOOP_INTERVAL_SECONDS:
            raise _StopLoopError

    monkeypatch.setattr(loop.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoopError):
        asyncio.run(loop.run_loop(AppConfig()))

    assert "streaming=false, someone_home=true, bed_time=false" in caplog.text


def test_run_loop_survives_unreachable_services(monkeypatch, caplog):
    config = AppConfig.model_validate(
        {"qbittorrent_instances": [{"url": "http://qbt.invalid", "username": "u", "password": "p"}]}
    )
    iterations = 0

    async def fake_sleep(delay):
        nonlocal iterations
        iterations += 1
        if iterations == 2:
            raise _StopLoopError

    async def unreachable(*_args, **_kwargs):
        raise ConnectionError

    async def boom(*_args, **_kwargs):
        raise RuntimeError

    monkeypatch.setattr(loop.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(loop.QbittorrentClient, "apply_streaming_limits", unreachable)
    monkeypatch.setattr(loop, "_check_active_streams", boom)

    with pytest.raises(_StopLoopError):
        asyncio.run(loop.run_loop(config))

    assert iterations == 2
    assert "Failed to set streaming limits" in caplog.text
    assert "Unexpected error in main loop" in caplog.text
