"""Jellyfin client tests."""

import asyncio
from http import HTTPStatus

from qbt_shaper.config import JellyfinConfig
from qbt_shaper.services.jellyfin import JellyfinClient
from tests.mocks import FakeResponse, FakeSession, JellyfinAuth, JellyfinSession, as_client_session

CONFIG = JellyfinConfig(url="http://jellyfin/", username="u", password="p")


def test_has_active_streams_logs_in_and_detects_playback():
    session = FakeSession(
        FakeResponse(JellyfinAuth()),
        FakeResponse([JellyfinSession(NowPlayingItem={"Name": "A Movie"}), JellyfinSession()]),
    )

    assert asyncio.run(JellyfinClient(CONFIG, as_client_session(session)).has_active_streams()) is True
    assert session.requests == [
        ("POST", "http://jellyfin/Users/AuthenticateByName"),
        ("GET", "http://jellyfin/Sessions"),
    ]


def test_has_active_streams_reauthenticates_on_401():
    session = FakeSession(
        FakeResponse(JellyfinAuth()),
        FakeResponse(status=HTTPStatus.UNAUTHORIZED),
        FakeResponse(JellyfinAuth()),
        FakeResponse([JellyfinSession()]),
    )

    assert asyncio.run(JellyfinClient(CONFIG, as_client_session(session)).has_active_streams()) is False
    assert [method for method, _ in session.requests] == ["POST", "GET", "POST", "GET"]
