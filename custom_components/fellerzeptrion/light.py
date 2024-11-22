"""Implementation of the Light Entry for Feller Zeptrion integration."""

import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Feller Zeptrion light entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]
    channels = data["channels"]
    network_info = data["network"]
    lights = []

    for ch_name, ch_info in channels.items():
        if ch_info["category"] == 1:
            lights.append(FellerZeptrionLight(hub, ch_name, ch_info, network_info))

    async_add_entities(lights, update_before_add=True)


class FellerZeptrionLight(LightEntity):
    """Implementation of the Light Entry for Feller Zeptrion integration."""

    def __init__(self, hub, channel_id, channel_info, network_info) -> None:
        """Initialize the light."""
        self._hub = hub
        self._channel_id = channel_info["id"]
        self._channel_info = channel_info
        self._mac_address = network_info['mac']
        self._state = None
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF
        self._attr_unique_id = f"{channel_info['name']}_{channel_id}_{self._mac_address}"
        self._attr_should_poll = True

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._channel_info["name"]

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac_address)},
            manufacturer="Feller Zeptrion",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._hub.turn_light_on(self._channel_id)
        await self.async_update()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._hub.turn_light_off(self._channel_id)
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the light state."""
        self._state = await self._hub.get_light_state(self._channel_id)

    async def async_added_to_hass(self) -> None:
        """Update the light state when added to hass."""
        await super().async_added_to_hass()
        await self.async_update()
