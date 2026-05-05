"""Configuration loading from a JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from .utils.logger import get_logger

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "qbt-shaper" / "config.json"


logger = get_logger(__name__)

class ServiceConfig(BaseModel):
    """Base configuration for a service instance."""

    url: str
    username: str
    password: SecretStr


class JellyfinConfig(ServiceConfig):
    """Configuration for a Jellyfin instance."""


class DispatcharrConfig(ServiceConfig):
    """Configuration for a Dispatcharr instance."""


class QbittorrentConfig(ServiceConfig):
    """Configuration for a qBittorrent instance."""


class AppConfig(BaseSettings):
    """Full application configuration, loaded from a JSON file."""

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
    )

    jellyfin_instances: list[JellyfinConfig] = []
    dispatcharr_instances: list[DispatcharrConfig] = []
    qbittorrent_instances: list[QbittorrentConfig] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        **_kwargs: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return ()


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

    logger.info("Loading config from %s", config_path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    logger.debug("Raw config data: %s", json.dumps(raw, indent=2))
    return AppConfig.model_validate(raw)
