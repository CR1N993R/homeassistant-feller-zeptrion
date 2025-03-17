"""Config flow for Feller Zeptrion integration."""
import logging

import aiohttp
from aiohttp import ClientTimeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .hub import FellerZeptrionHub
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

HOST_SCHEMA = vol.Schema({vol.Required("host"): str})


class MyHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Feller Zeptrion."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_info: dict | None = None
        self._channels: dict | None = None
        self._data: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step of the flow: gathering the host."""
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
                    self._data["host"] = user_input["host"]
                    return await self.async_step_channels()

        return self.async_show_form(step_id="user", data_schema=HOST_SCHEMA, errors=errors)

    async def async_step_channels(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the second step of the flow: gathering channel names."""
        errors = {}
        if user_input is not None:
            # Combine the host with the channel data
            entry_data = {**self._data, **user_input}
            return self.async_create_entry(title=user_input["Hub Name"], data=entry_data)

        channel_schema = self.get_channel_schema()
        if channel_schema is None:
            return self.async_abort(reason="no_channels")

        return self.async_show_form(step_id="channels", data_schema=channel_schema, errors=errors)

    def get_channel_schema(self) -> vol.Schema | None:
        """Generate the schema for channel configuration."""
        if not self._device_info or not self._channels:
            return None

        # Fix the f-string quoting issue by using double quotes for nested quotes
        fields = {
            vol.Required("Hub Name", default=f'Feller Zeptrion Zapp {self._device_info["serial_number"]}'): str
        }
        for ch_info in self._channels.values():
            if ch_info["category"] != -1:
                key = vol.Required(f'Channel {ch_info["id"]} Name', default=ch_info["name"])
                fields[key] = str
        return vol.Schema(fields)
