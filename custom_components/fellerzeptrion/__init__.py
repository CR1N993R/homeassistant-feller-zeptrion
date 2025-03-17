"""Init script for the Feller Zeptrion integration."""
import logging

from async_upnp_client import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import FellerZeptrionHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["cover", "light"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Feller Zeptrion integration from a config entry."""
    session = aiohttp.ClientSession()
    hub = FellerZeptrionHub(entry.data["host"], session)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "channels": await hub.get_channel_descriptions(entry.data),
        "network": await hub.get_network_info(),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and clean up resources."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub = hass.data[DOMAIN][entry.entry_id]["hub"]
        await hub.close()  # Close the aiohttp session
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
