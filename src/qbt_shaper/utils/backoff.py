"""Per-service failure backoff to keep an unreachable endpoint from spamming the logs."""

import time
from typing import TYPE_CHECKING

from .logger import get_logger

if TYPE_CHECKING:
    from types import TracebackType

BACKOFF_AFTER_FAILURES = 2
BACKOFF_SECONDS = 60

logger = get_logger(__name__)


class BackoffActiveError(Exception):
    """Raised instead of making a request while the service is backed off. Callers skip it silently."""


class Backoff:
    """Context manager wrapping each request to one service.

    After BACKOFF_AFTER_FAILURES consecutive failures, requests are refused for
    BACKOFF_SECONDS. One failed retry after the window backs off again.
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._failures = 0
        self._retry_at = 0.0

    def __enter__(self) -> None:
        if time.monotonic() < self._retry_at:
            raise BackoffActiveError(self._name)

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        if exc is None:
            if self._failures >= BACKOFF_AFTER_FAILURES:
                logger.info("%s reachable again", self._name)
            self._failures = 0
        elif isinstance(exc, Exception):
            self._failures += 1
            if self._failures >= BACKOFF_AFTER_FAILURES:
                self._retry_at = time.monotonic() + BACKOFF_SECONDS
                logger.warning("%s failing (%r), retrying in %ds", self._name, exc, BACKOFF_SECONDS)
