"""Home Assistant API client for presence detection."""

from typing import TYPE_CHECKING

from homeassistant_api import AsyncClient

from qbt_shaper.utils.logger import get_logger

if TYPE_CHECKING:
    from qbt_shaper.config import HomeAssistantConfig
else:
    HomeAssistantConfig = object

logger = get_logger(__name__)


class HomeAssistantClient:
    """Client for querying Home Assistant entity states."""

    def __init__(self, config: HomeAssistantConfig) -> None:
        self._config = config

    def is_configured(self) -> bool:
        """Return True if the client has a URL, token, and at least one entity configured."""
        return bool(self._config.url and self._config.token and self._config.presence_entities)

    async def any_entity_home(self) -> bool:
        """Return True if any of the configured presence entities reports state 'home'."""
        try:
            async with AsyncClient(self._config.url, self._config.token) as client:
                for entity_id in self._config.presence_entities:
                    try:
                        state = await client.get_state(entity_id=entity_id)
                        if state.state == "home":
                            logger.debug("Entity %s is home", entity_id)
                            return True
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Failed to get state for entity %s: %s", entity_id, type(e).__name__)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to connect to Home Assistant at %s: %s", self._config.url, type(e).__name__)
        return False
