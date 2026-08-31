"""Config tests."""

import pytest

from qbt_shaper.config import (
    AppConfig,
    BedtimeConfig,
    QbittorrentConfig,
    _parse_time_to_iso,
    load_config,
    write_config,
)


def test_load_config_missing_file(tmp_path) -> None:
    config = load_config(tmp_path / "config.json")

    assert config == AppConfig()


def test_config_round_trip(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        qbittorrent_instances=[
            QbittorrentConfig(url="http://localhost", username="u", password="p", force_recheck_errored=True),
        ],
    )

    write_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded == config
    assert loaded.qbittorrent_instances[0].force_recheck_errored is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("22:00+10:00", "22:00+10:00"),
        ("10:00 PM+10:00", "22:00+10:00"),
        ("7am-05:00", "07:00-05:00"),
    ],
)
def test_parse_time_to_iso(value, expected) -> None:
    assert _parse_time_to_iso(value) == expected


def test_parse_time_to_iso_invalid() -> None:
    with pytest.raises(ValueError, match="Cannot parse time string"):
        _parse_time_to_iso("bedtime o'clock")


def test_bedtime_is_active() -> None:
    assert BedtimeConfig(enabled=False, start="00:00+00:00", stop="23:59+00:00").is_active() is False
    assert BedtimeConfig(enabled=True, start="00:00+00:00", stop="23:59+00:00").is_active() is True
