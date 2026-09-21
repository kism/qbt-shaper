"""Backoff tests."""

import pytest

from qbt_shaper.utils import backoff
from qbt_shaper.utils.backoff import Backoff, BackoffActiveError


def _fail(b: Backoff) -> None:
    with pytest.raises(ConnectionError), b:
        raise ConnectionError


def test_backoff_after_two_failures(monkeypatch):
    now = 1000.0
    monkeypatch.setattr(backoff.time, "monotonic", lambda: now)
    b = Backoff("svc")

    _fail(b)
    with b:  # one failure: still allowed, and success resets the count
        pass
    _fail(b)
    _fail(b)  # second consecutive failure starts the backoff

    with pytest.raises(BackoffActiveError), b:
        pass

    now += backoff.BACKOFF_SECONDS
    _fail(b)  # retry after the window fails -> backed off again immediately
    with pytest.raises(BackoffActiveError), b:
        pass

    now += backoff.BACKOFF_SECONDS
    with b:  # recovered
        pass
    _fail(b)
    with b:  # count was reset, so one failure doesn't back off
        pass
