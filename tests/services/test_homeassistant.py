"""Home Assistant client tests."""

import asyncio

from qbt_shaper.config import HomeAssistantConfig
from qbt_shaper.services import homeassistant
from qbt_shaper.services.homeassistant import HomeAssistantClient
from tests.mocks import FakeHaClient

CONFIG = HomeAssistantConfig(url="http://ha", token="t", presence_entities=["device_tracker.phone"])


def test_is_configured():
    assert HomeAssistantClient(CONFIG).is_configured() is True
    assert HomeAssistantClient(HomeAssistantConfig()).is_configured() is False


def test_any_entity_home(monkeypatch):
    monkeypatch.setattr(homeassistant, "AsyncClient", FakeHaClient)

    assert asyncio.run(HomeAssistantClient(CONFIG).any_entity_home()) is False

    monkeypatch.setattr(FakeHaClient, "states", {"device_tracker.phone": "home"})
    assert asyncio.run(HomeAssistantClient(CONFIG).any_entity_home()) is True
