"""Config tests."""

from qbt_shaper.config import AppConfig, QbittorrentConfig, load_config, write_config


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
