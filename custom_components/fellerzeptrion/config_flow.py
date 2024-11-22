"""Config flow for Feller Zeptrion integration."""
import logging

import aiohttp
from aiohttp import ClientTimeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from . import FellerZeptrionHub
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

host_schema = vol.Schema(
    {
        vol.Required("host"): str,
    }
)


class MyHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_info = None
        self._channels = None
        self._data = {}

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the first step of the flow: gathering the host."""
        errors = {}
        if user_input is not None:
            session = aiohttp.ClientSession(timeout=ClientTimeout(1))
            hub = FellerZeptrionHub(user_input["host"], session)
            channels = await hub.get_channel_descriptions()
            device_info = await hub.get_device_info()
            await session.close()
            if channels is None or device_info is None:
                errors = {"host": "Could not connect to Feller Zeptrion Hub"}
            else:
                self._channels = channels
                self._device_info = device_info
                channel_schema = self.get_channel_schema()
                if channel_schema is None:
                    errors = {"host": "Zeptrion hub has no configured channels"}
                else:
                    # Store the host and transition to the next step
                    self._data["host"] = user_input["host"]
                    return await self.async_step_channels()

        return self.async_show_form(step_id="user", data_schema=host_schema, errors=errors)

    async def async_step_channels(self, user_input=None) -> ConfigFlowResult:
        """Handle the second step of the flow: gathering channel information."""
        errors = {}
        if user_input is not None:
            # Combine the host with the channel data
            entry_data = {**self._data, **user_input}
            return self.async_create_entry(title=user_input['Hub Name'], data=entry_data)

        # Generate the schema for channel data
        channel_schema = self.get_channel_schema()
        if channel_schema is None:
            return self.async_abort(reason="no_channels")

        return self.async_show_form(step_id="channels", data_schema=channel_schema, errors=errors)

    def get_channel_schema(self):
        """Get the channel schema for the configuration step."""
        fields = {vol.Required('Hub Name', default=f'Feller Zeptrion Zapp {self._device_info['serial_number']}'): str}
        for ch_info in self._channels.values():
            if ch_info["category"] != -1:
                key = vol.Required(f'Channel {ch_info["id"]} Name', default=ch_info['name'])
                fields[key] = str
        if not fields:
            return None
        return vol.Schema(fields)
