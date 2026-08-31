"""The conftest.py file serves as a means of providing fixtures for an entire directory.

Fixtures defined in a conftest.py can be used by any test in that package without needing to import them.
"""

import pytest
import qbittorrentapi

from qbt_shaper.config import QbittorrentConfig, QbittorrentSpeedConfig
from qbt_shaper.services.qbittorrent import QbittorrentClient
from tests.mocks import FakeQbtClient


@pytest.fixture
def qbt(monkeypatch):
    """Factory for QbittorrentClient instances backed by FakeQbtClient."""
    monkeypatch.setattr(qbittorrentapi, "Client", FakeQbtClient)

    def _make(speed: QbittorrentSpeedConfig | None = None, **config_kwargs) -> QbittorrentClient:
        config = QbittorrentConfig(url="http://qbt", username="u", password="p", **config_kwargs)
        return QbittorrentClient(config, speed or QbittorrentSpeedConfig())

    return _make
