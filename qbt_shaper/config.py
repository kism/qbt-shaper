"""Configuration loading from environment variables."""

from __future__ import annotations

import os
import re

from pydantic import BaseModel, SecretStr

ENV_PREFIX = "QBTSHP"


class ConfigError(ValueError):
    """Raised when required configuration environment variables are missing."""

    def __init__(self, service: str, instance: int, missing_vars: list[str]) -> None:
        super().__init__(f"Missing environment variables for {service} instance {instance}: {missing_vars}")


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


class AppConfig(BaseModel):
    """Full application configuration."""

    jellyfin_instances: list[JellyfinConfig]
    dispatcharr_instances: list[DispatcharrConfig]
    qbittorrent_instances: list[QbittorrentConfig]


def _find_instance_indices(prefix: str) -> list[int]:
    """Scan environment variables to find numbered instance indices for a given prefix."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)_")
    indices: set[int] = set()
    for key in os.environ:
        if m := pattern.match(key):
            indices.add(int(m.group(1)))
    return sorted(indices)


def _load_service_configs[T: ServiceConfig](service_name: str, model: type[T]) -> list[T]:
    """Discover and load numbered service configs from environment variables.

    Reads QBTSHP_{SERVICE_NAME}_{N}_URL, QBTSHP_{SERVICE_NAME}_{N}_USER,
    and QBTSHP_{SERVICE_NAME}_{N}_PASSWORD for each discovered instance N.
    """
    prefix = f"{ENV_PREFIX}_{service_name.upper()}_"
    configs: list[T] = []

    for idx in _find_instance_indices(prefix):
        instance_prefix = f"{prefix}{idx}_"
        url = os.environ.get(f"{instance_prefix}URL")
        username = os.environ.get(f"{instance_prefix}USER")
        password = os.environ.get(f"{instance_prefix}PASSWORD")

        if url is None or username is None or password is None:
            missing = [
                name
                for name, val in [
                    (f"{instance_prefix}URL", url),
                    (f"{instance_prefix}USER", username),
                    (f"{instance_prefix}PASSWORD", password),
                ]
                if val is None
            ]
            raise ConfigError(service_name, idx, missing)

        configs.append(model.model_validate({"url": url, "username": username, "password": password}))

    return configs


def load_config() -> AppConfig:
    """Load application configuration from environment variables."""
    return AppConfig(
        jellyfin_instances=_load_service_configs("JELLYFIN", JellyfinConfig),
        dispatcharr_instances=_load_service_configs("DISPATCHARR", DispatcharrConfig),
        qbittorrent_instances=_load_service_configs("QBITTORRENT", QbittorrentConfig),
    )
