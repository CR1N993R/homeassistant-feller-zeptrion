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
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
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
    """Implementation of the Cover Entry for Feller Zeptrion."""

    def __init__(self, hub, channel_id, channel_info, network_info) -> None:
        """Initialize the cover."""
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

    previous_action = None

    @property
    def name(self) -> str:
        """Return the name of the cover."""
        return self._channel_info["name"]

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        return self._attr_is_closed

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac_address)},
            manufacturer="Feller Zeptrion",
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._hub.blind_open(self._channel_id)
        self.previous_action = "open"
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._hub.blind_close(self._channel_id)
        self.previous_action = "close"
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop opening or closing of the cover."""
        if self.previous_action is None:
            return
        await self._hub.blind_stop(self._channel_id, self.previous_action)
        self.previous_action = None
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Tilt the cover open."""
        await self._hub.blind_open_tilt(self._channel_id)
        self.previous_action = None
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Tilt the cover close."""
        if self.previous_action == "close":
            return
        await self._hub.blind_close_tilt(self._channel_id)
        self.previous_action = None
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def toggle(self, **kwargs: Any) -> None:
        """Toggle the cover."""
        await self._hub.blind_toggle(self._channel_id)
        self.previous_action = None
        self._attr_is_closed = False
        self.async_write_ha_state()
