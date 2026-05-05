"""Configuration loading from a JSON file."""

import json
from pathlib import Path

from pydantic import BaseModel

from .utils.logger import get_logger

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "qbt-shaper" / "config.json"


logger = get_logger(__name__)


class ServiceConfig(BaseModel):
    """Base configuration for a service instance."""

    url: str
    username: str
    password: str


class JellyfinConfig(ServiceConfig):
    """Configuration for a Jellyfin instance."""


class DispatcharrConfig(ServiceConfig):
    """Configuration for a Dispatcharr instance."""


class QbittorrentConfig(ServiceConfig):
    """Configuration for a qBittorrent instance."""


class QbittorrentSpeedConfig(BaseModel):
    """Global speed limit configuration expressed as percentages of internet bandwidth."""

    dl_max_kbps: int = 0
    ul_max_kbps: int = 0
    dl_streaming_percent: int = 0
    ul_streaming_percent: int = 0
    dl_vacant_percent: int = 0
    ul_vacant_percent: int = 0
    dl_present_percent: int = 0
    ul_present_percent: int = 0


class HomeAssistantConfig(BaseModel):
    """Configuration for Home Assistant presence detection."""

    url: str = ""
    token: str = ""
    presence_entities: list[str] = []


class AppConfig(BaseModel):
    """Full application configuration, loaded from a JSON file."""

    jellyfin_instances: list[JellyfinConfig] = []
    dispatcharr_instances: list[DispatcharrConfig] = []
    qbittorrent_instances: list[QbittorrentConfig] = []
    qbittorrent_speed: QbittorrentSpeedConfig = QbittorrentSpeedConfig()
    home_assistant: HomeAssistantConfig = HomeAssistantConfig()


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load application configuration from a JSON file.

    If the file does not exist, write a default config and return it.
    """
    if not config_path.exists():
        logger.info("Config file not found at %s, writing default config", config_path)
        default = AppConfig()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            default.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return default

    logger.debug("Loading config from %s", config_path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def write_config(config: AppConfig, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Write the config to disk, filling in any missing fields with their defaults."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Wrote config to %s", config_path)

