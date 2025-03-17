"""Utility class for API calls for the Feller Zeptrion integration."""

import logging
from enum import IntEnum

import aiohttp
import xml.etree.ElementTree as StdET

_LOGGER = logging.getLogger(__name__)

COMMAND_ON = "on"
COMMAND_OFF = "off"
COMMAND_DIM_UP = "dim_up_200"
COMMAND_DIM_DOWN = "dim_down_200"
COMMAND_TOGGLE = "toggle"

BASE_URL = "http://{host}"
CHANNEL_DESCRIPTION_ENDPOINT = "/zrap/chdes"
CHANNEL_STATES_ENDPOINT = "/zrap/chscan"
SEND_COMMAND_ENDPOINT = "/zrap/chctrl"
CHANNEL_NOTIFY_ENDPOINT = "/zrap/chnotify"
NETWORK_INFO_ENDPOINT = "/zrap/net"
DEVICE_INFO_ENDPOINT = "/zrap/id"


class DeviceCategory(IntEnum):
    """The category of the devices connected to the Hub."""
    UNKNOWN = -1
    LIGHT = 1
    BLIND = 5


class FellerZeptrionHub:
    """Utility class for API calls for the Feller Zeptrion integration."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the Feller Zeptrion hub."""
        self._host = host
        self._session = session

    async def close(self) -> None:
        """Close the aiohttp session."""
        await self._session.close()

    async def get_channel_descriptions(self, channel_names: dict | None = None) -> dict | None:
        """Return the channel descriptions of the hub."""
        data = await self.__fetch_channel_description()
        if data is None:
            return None
        return self.parse_channel_descriptions(data, channel_names)

    async def get_network_info(self) -> dict | None:
        """Return the network info of the hub."""
        data = await self.__fetch_network_info()
        if data is None:
            return None
        return self.parse_network_info(data)

    async def get_device_info(self) -> dict | None:
        """Return the device info of the hub."""
        data = await self.__fetch_device_info()
        if data is None:
            return None
        return self.parse_device_info(data)

    async def turn_light_on(self, channel: str) -> None:
        """Send the command to turn the light on."""
        update = self.__await_update()
        await self.__send_command(channel, COMMAND_ON)
        await update

    async def turn_light_off(self, channel: str) -> None:
        """Send the command to turn the light off."""
        update = self.__await_update()
        await self.__send_command(channel, COMMAND_OFF)
        await update

    async def get_light_state(self, channel: str) -> bool:
        """Fetch and return the state of the light."""
        channel_states = await self.__fetch_channel_states()
        state = self.parse_channel_state(channel, channel_states)
        if state is None:
            return False
        try:
            return int(state) > 0
        except ValueError:
            _LOGGER.error("Invalid state value for channel %s: %s", channel, state)
            return False

    async def blind_open(self, channel: str) -> None:
        """Send the command to open the blind."""
        await self.__send_command(channel, COMMAND_ON)

    async def blind_close(self, channel: str) -> None:
        """Send the command to close the blind."""
        await self.__send_command(channel, COMMAND_OFF)

    async def blind_stop(self, channel: str, previous_action: str) -> None:
        """Send the command to stop the blind based on the previous action."""
        if previous_action == "open":
            await self.blind_close(channel)
        else:
            await self.blind_open(channel)

    async def blind_open_tilt(self, channel: str) -> None:
        """Send the command to tilt the blind open."""
        await self.__send_command(channel, COMMAND_DIM_UP)

    async def blind_close_tilt(self, channel: str) -> None:
        """Send the command to tilt the blind close."""
        await self.__send_command(channel, COMMAND_DIM_DOWN)

    async def blind_toggle(self, channel: str) -> None:
        """Toggle the blind state."""
        await self.__send_command(channel, COMMAND_ON)

    def parse_channel_state(self, channel: str, channel_states: str) -> str | None:
        """Parse the state of a specific channel from the channel states XML."""
        try:
            states = StdET.fromstring(channel_states)
            channel_element = states.find(f"ch{channel}")
            return self.safe_find_text(channel_element, "val")
        except StdET.ParseError as e:
            _LOGGER.error("Failed to parse channel states: %s", e)
            return None

    def parse_device_info(self, device_info: str) -> dict | None:
        """Parse and return the device info from XML."""
        try:
            info = StdET.fromstring(device_info)
            hw = self.safe_find_text(info, "hw")
            sn = self.safe_find_text(info, "sn")
            hw_type = self.safe_find_text(info, "type")
            sw = self.safe_find_text(info, "sw")
        except StdET.ParseError as e:
            _LOGGER.error("Failed to parse device info: %s", e)
            return None
        return {
            "hardware_version": hw,
            "serial_number": sn,
            "type": hw_type,
            "software_version": sw,
        }

    def parse_network_info(self, network_info: str) -> dict | None:
        """Parse and return network information from XML."""
        try:
            network = StdET.fromstring(network_info)
            mac = self.safe_find_text(network, "mac")
        except StdET.ParseError as e:
            _LOGGER.error("Failed to parse network information: %s", e)
            return None
        return {"mac": mac}

    def parse_channel_descriptions(self, xml_data: str, channel_names: dict | None = None) -> dict:
        """Parse channel descriptions from XML data."""
        channels: dict = {}
        try:
            raw_channels = StdET.fromstring(xml_data)
            for channel in raw_channels:
                ch_id = channel.tag.replace("ch", "")
                key = f"Channel {ch_id} Name"
                name = (
                    channel_names.get(key)
                    if channel_names and key in channel_names
                    else self.safe_find_text(channel, "name", "Unnamed")
                )
                group = self.safe_find_text(channel, "group", "Ungrouped")
                cat = int(self.safe_find_text(channel, "cat", str(DeviceCategory.UNKNOWN)))
                if cat == DeviceCategory.UNKNOWN:
                    continue  # Skip disconnected channels
                channels[channel.tag] = {
                    "id": ch_id,
                    "name": name,
                    "group": group,
                    "category": cat,
                }
        except StdET.ParseError as e:
            _LOGGER.error("Failed to parse channel descriptions: %s", e)
        return channels

    def safe_find_text(self, element: StdET.Element | None, tag: str, default: str | None = None) -> str | None:
        """Safely find text in an XML element."""
        try:
            found = element.find(tag) if element is not None else None
            return found.text.strip() if found is not None and found.text else default
        except AttributeError:
            return default

    async def __make_request(self, method: str, endpoint: str, **kwargs) -> str | None:
        """Make an HTTP request to the hub and return the text response."""
        url = BASE_URL.format(host=self._host) + endpoint
        try:
            async with self._session.request(method, url, **kwargs) as response:
                if response.status in (200, 302):
                    return await response.text()
                error_text = await response.text()
                _LOGGER.error("HTTP %s Error for %s: %s", response.status, url, error_text)
        except aiohttp.ClientError as e:
            _LOGGER.error("Client error during request to %s: %s", url, e)
        except TimeoutError:
            _LOGGER.warning("Request to %s timed out", url)
        except Exception:
            _LOGGER.exception("Unexpected error during request to %s", url)
        return None

    async def __fetch_channel_description(self) -> str | None:
        return await self.__make_request("GET", CHANNEL_DESCRIPTION_ENDPOINT)

    async def __fetch_channel_states(self) -> str | None:
        return await self.__make_request("GET", CHANNEL_STATES_ENDPOINT)

    async def __await_update(self) -> str | None:
        return await self.__make_request("GET", CHANNEL_NOTIFY_ENDPOINT, timeout=1)

    async def __fetch_network_info(self) -> str | None:
        return await self.__make_request("GET", NETWORK_INFO_ENDPOINT)

    async def __fetch_device_info(self) -> str | None:
        return await self.__make_request("GET", DEVICE_INFO_ENDPOINT)

    async def __send_command(self, channel: str, command: str) -> None:
        """Send a command to a specific channel."""
        data = {f"cmd{channel}": command}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        await self.__make_request("POST", SEND_COMMAND_ENDPOINT, headers=headers, data=data)