import argparse
import logging

import pytest

from qbt_shaper import __main__


def test_main(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO)

    mock_args = argparse.Namespace(v=0, message="Hello, World!")
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    __main__.main()
    assert "Hello, World!" in caplog.text
    assert "qbt-shaper v0.0.1" in caplog.text
    assert "Hello, World!" in caplog.text
