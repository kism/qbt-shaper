"""Dispatcharr client tests."""

import asyncio
from http import HTTPStatus

from qbt_shaper.config import DispatcharrConfig
from qbt_shaper.services.dispatcharr import DispatcharrClient
from tests.mocks import DispatcharrStatus, DispatcharrToken, FakeResponse, FakeSession, as_client_session

CONFIG = DispatcharrConfig(url="http://dispatcharr/", username="u", password="p")


def test_has_active_streams_logs_in_and_counts_channels():
    session = FakeSession(FakeResponse(DispatcharrToken()), FakeResponse(DispatcharrStatus(count=2)))

    assert asyncio.run(DispatcharrClient(CONFIG, as_client_session(session)).has_active_streams()) is True
    assert session.requests == [
        ("POST", "http://dispatcharr/api/accounts/token/"),
        ("GET", "http://dispatcharr/proxy/ts/status"),
    ]


def test_has_active_streams_reauthenticates_on_401():
    session = FakeSession(
        FakeResponse(DispatcharrToken()),
        FakeResponse(status=HTTPStatus.UNAUTHORIZED),
        FakeResponse(DispatcharrToken()),
        FakeResponse(DispatcharrStatus(count=0)),
    )

    assert asyncio.run(DispatcharrClient(CONFIG, as_client_session(session)).has_active_streams()) is False
    assert [method for method, _ in session.requests] == ["POST", "GET", "POST", "GET"]
