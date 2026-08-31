"""Logger unit tests."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from qbt_shaper.utils.logger import (
    TRACE_LEVEL_NUM,
    CustomLogger,
    _add_file_handler,
    setup_logger,
    setup_logger_cli,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture
else:
    MockerFixture = object


@pytest.fixture
def logger() -> Generator[logging.Logger]:
    """Logger to use in unit tests, including cleanup."""
    logger = logging.getLogger("TEST_LOGGER")

    assert len(logger.handlers) == 0  # Check the logger has no handlers

    yield logger

    # Reset the test object since it will persist.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def test_logging_permissions_error(logger: CustomLogger, tmp_path: Path, mocker: MockerFixture) -> None:
    """Test logging, mock a permission error."""
    mock_open_func = mocker.mock_open(read_data="")
    mock_open_func.side_effect = PermissionError("Permission denied")

    mocker.patch("builtins.open", mock_open_func)

    # TEST: That a permissions error is raised when open() results in a permissions error.
    with pytest.raises(PermissionError):
        _add_file_handler(logger, tmp_path)


def test_config_logging_to_dir(logger: CustomLogger, tmp_path: Path) -> None:
    """TEST: Correct exception is caught when you try log to a folder."""
    with pytest.raises(IsADirectoryError):
        _add_file_handler(logger, tmp_path)


def test_handler_console_added(logger: CustomLogger) -> None:
    """Test logging console handler."""
    log_path = None
    log_level = "INFO"

    # TEST: Only one handler (console), should exist when no logging path provided
    setup_logger(log_level=log_level, log_path=log_path, in_logger=logger)
    assert len(logger.handlers) == 1

    # TEST: If a console handler exists, another one shouldn't be created
    setup_logger(log_level=log_level, log_path=log_path, in_logger=logger)
    assert len(logger.handlers) == 1


def test_handler_file_added(logger: CustomLogger, tmp_path: Path) -> None:
    """Test logging file handler."""
    log_path = Path(tmp_path) / "test.log"
    log_level = "INFO"

    # TEST: Two handlers when logging to file expected
    setup_logger(log_level=log_level, log_path=log_path, in_logger=logger)
    assert len(logger.handlers) == 2  # noqa: PLR2004 A console and a file handler are expected

    # TEST: Two handlers when logging to file expected, another one shouldn't be created
    setup_logger(log_level=log_level, log_path=log_path, in_logger=logger)
    assert len(logger.handlers) == 2  # noqa: PLR2004 A console and a file handler are expected


@pytest.mark.parametrize(
    ("verbosity", "expected_level"),
    [
        (0, logging.INFO),  # <no -v>
        (1, logging.DEBUG),  # -v
        (2, TRACE_LEVEL_NUM),  # -vv
    ],
)
def test_logger_setup_cli(
    logger: CustomLogger,
    caplog: pytest.LogCaptureFixture,
    verbosity: int,
    expected_level: int,
) -> None:
    setup_logger_cli(verbosity=verbosity, in_logger=logger)
    assert logger.getEffectiveLevel() == expected_level
