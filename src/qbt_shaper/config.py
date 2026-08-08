"""Configuration loading from a JSON file."""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from .utils.logger import get_logger

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "qbt-shaper" / "config.json"
if os.environ.get("QBT_SHAPER_CONFIG_PATH"):
    DEFAULT_CONFIG_PATH = Path(os.environ["QBT_SHAPER_CONFIG_PATH"])


logger = get_logger(__name__)


def _parse_time_to_iso(value: str) -> str:
    """Parse a time string and normalise to HH:MM±HH:MM (ISO 24-hour with UTC offset).

    Accepts e.g. '22:00', '10:00 PM', '10:00pm', '22:00+10:00'.
    If no UTC offset is present the local system timezone offset is used.
    """
    value = value.strip()

    tz_match = re.search(r"([+-])(\d{1,2}):(\d{2})$", value)
    if tz_match:
        sign_char = tz_match.group(1)
        tz_formatted = f"{sign_char}{int(tz_match.group(2)):02d}:{tz_match.group(3)}"
        time_part = value[: tz_match.start()].strip()
    else:
        local_now = datetime.now().astimezone()
        offset = local_now.utcoffset()
        if offset is None:
            msg = "Could not determine local timezone offset"
            raise ValueError(msg)
        total_secs = int(offset.total_seconds())
        sign_char = "+" if total_secs >= 0 else "-"
        total_secs_abs = abs(total_secs)
        tz_formatted = f"{sign_char}{total_secs_abs // 3600:02d}:{(total_secs_abs % 3600) // 60:02d}"
        time_part = value

    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p"):
        try:
            parsed = datetime.strptime(time_part.upper(), fmt)
        except ValueError:
            continue
        else:
            return f"{parsed.hour:02d}:{parsed.minute:02d}{tz_formatted}"

    msg = f"Cannot parse time string {value!r}. Use formats like '22:00', '10:00 PM', '22:00+10:00'"
    raise ValueError(msg)


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

    priority: int = 1
    """Throttling priority. Lower number = higher priority. Instances at the same level are peers."""

    force_recheck_errored: bool = False
    """Periodically force a recheck of all torrents in an errored state."""


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


class BedtimeConfig(BaseModel):
    """Configuration for bedtime mode, which overrides presence detection to 'vacant'."""

    enabled: bool = False
    start: str = Field(default="22:00", validate_default=True)
    stop: str = Field(default="07:00", validate_default=True)

    @field_validator("start", "stop", mode="before")
    @classmethod
    def _normalize_time(cls, v: str) -> str:
        return _parse_time_to_iso(v)

    def is_active(self) -> bool:
        """Return True if the current time falls within the configured bedtime window."""
        if not self.enabled:
            return False
        start_match = re.fullmatch(r"(\d{2}):(\d{2})([+-])(\d{2}):(\d{2})", self.start)
        stop_match = re.fullmatch(r"(\d{2}):(\d{2})([+-])(\d{2}):(\d{2})", self.stop)
        if not start_match or not stop_match:
            logger.warning("Bedtime config has unexpected time format, skipping bedtime check")
            return False
        sign = 1 if start_match.group(3) == "+" else -1
        tz = timezone(timedelta(hours=sign * int(start_match.group(4)), minutes=sign * int(start_match.group(5))))
        now = datetime.now(tz=tz)
        current_min = now.hour * 60 + now.minute
        start_min = int(start_match.group(1)) * 60 + int(start_match.group(2))
        stop_min = int(stop_match.group(1)) * 60 + int(stop_match.group(2))
        if start_min <= stop_min:
            return start_min <= current_min <= stop_min
        # Midnight-crossing range (e.g. 22:00 → 07:00)
        return current_min >= start_min or current_min <= stop_min


class AppConfig(BaseModel):
    """Full application configuration, loaded from a JSON file."""

    jellyfin_instances: list[JellyfinConfig] = []
    dispatcharr_instances: list[DispatcharrConfig] = []
    qbittorrent_instances: list[QbittorrentConfig] = []
    qbittorrent_speed: QbittorrentSpeedConfig = QbittorrentSpeedConfig()
    home_assistant: HomeAssistantConfig = HomeAssistantConfig()
    bedtime: BedtimeConfig = BedtimeConfig()


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
    return AppConfig.model_validate(raw)


def write_config(config: AppConfig, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Write the config to disk, filling in any missing fields with their defaults."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Wrote config to %s", config_path)
