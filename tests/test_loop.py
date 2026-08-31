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
