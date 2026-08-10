import argparse
import logging

import pytest  # noqa: TC002

from qbt_shaper import __main__


def test_main(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    caplog.set_level(logging.INFO)

    mock_args = argparse.Namespace(v=0, config=tmp_path / "config.json")
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    async def fake_run_loop(config):
        pass

    monkeypatch.setattr(__main__, "run_loop", fake_run_loop)

    __main__.main()
    assert "qbt-shaper v" in caplog.text
