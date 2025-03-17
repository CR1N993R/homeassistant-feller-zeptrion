"""Implementation of the Cover Entry for Feller Zeptrion integration."""

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Feller Zeptrion cover entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]
    channels = data["channels"]
    network_info = data["network"]
    covers = []

    for ch_name, ch_info in channels.items():
        if ch_info["category"] == 5:
            covers.append(FellerZeptrionBlind(hub, ch_name, ch_info, network_info))
    async_add_entities(covers)


class FellerZeptrionBlind(CoverEntity):
    """Representation of a Feller Zeptrion blind cover."""

    def __init__(self, hub: Any, channel_id: str, channel_info: dict, network_info: dict) -> None:
        """Initialize the cover entity."""
        self._hub = hub
        self._channel_id = channel_info["id"]
        self._channel_info = channel_info
        self._mac_address = network_info['mac']
        self._attr_unique_id = f"{channel_info['name']}_{channel_id}_{self._mac_address}"
        self._attr_assumed_state = True
        self._attr_is_closed = None
        self._attr_supported_features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
        )
        self.previous_action: str | None = None

    @property
    def name(self) -> str:
        """Return the name of the cover."""
        return self._channel_info["name"]

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        return self._attr_is_closed

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac_address)},
            manufacturer="Feller Zeptrion",
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        try:
            await self._hub.blind_open(self._channel_id)
            self.previous_action = "open"
            self._attr_is_closed = False
        except Exception as err:
            _LOGGER.error("Error opening cover %s: %s", self.name, err)
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        try:
            await self._hub.blind_close(self._channel_id)
            self.previous_action = "close"
            self._attr_is_closed = True
        except Exception as err:
            _LOGGER.error("Error closing cover %s: %s", self.name, err)
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover movement."""
        if self.previous_action is None:
            return
        try:
            await self._hub.blind_stop(self._channel_id, self.previous_action)
            self.previous_action = None
            self._attr_is_closed = False
        except Exception as err:
            _LOGGER.error("Error stopping cover %s: %s", self.name, err)
        self.async_write_ha_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        try:
            await self._hub.blind_open_tilt(self._channel_id)
            self.previous_action = None
            self._attr_is_closed = False
        except Exception as err:
            _LOGGER.error("Error opening tilt for cover %s: %s", self.name, err)
        self.async_write_ha_state()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if self.previous_action == "close":
            return
        try:
            await self._hub.blind_close_tilt(self._channel_id)
            self.previous_action = None
            self._attr_is_closed = False
        except Exception as err:
            _LOGGER.error("Error closing tilt for cover %s: %s", self.name, err)
        self.async_write_ha_state()

    async def toggle(self, **kwargs: Any) -> None:
        """Toggle the cover state."""
        try:
            await self._hub.blind_toggle(self._channel_id)
            self.previous_action = None
            self._attr_is_closed = False
        except Exception as err:
            _LOGGER.error("Error toggling cover %s: %s", self.name, err)
        self.async_write_ha_state()
