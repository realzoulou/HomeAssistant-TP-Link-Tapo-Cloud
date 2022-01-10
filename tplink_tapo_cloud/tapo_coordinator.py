""" DataUpdateCoordinator for TP-Link Tapo Cloud devices."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Final
import async_timeout



from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from PyP100 import PyP100, PyP110

from .const import (
    DOMAIN,
    COORDINATOR_DATA_KEY_NAME,
    COORDINATOR_DATA_KEY_DEVICEINFO,
    COORDINATOR_DATA_KEY_ENERGY,
    MANUFACTURER,
    TAPOCLOUD_URL,
)

_LOGGER = logging.getLogger(__name__)

class TapoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tapo device data."""

    def __init__(
        self,
        hass: HomeAssistant,
        p1xx: PyP100.P100 | PyP110.P110,
        interval: timedelta,
        config_entry_unique_id: str,
    ) -> None:
        """Initialize."""

        self._hass = hass
        self._p1xx = p1xx
        self._config_entry_unique_id = config_entry_unique_id

        self._connected = False

        super().__init__(
            self._hass,
            _LOGGER,
            # Name of the data for logging purposes.
            name = DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval = interval,
            # Callable
            update_method = self._async_update_data
        )

    async def _async_update_data(self):
        """Update data via PyPI library."""

        try:
            data: dict[str, Any] = {}
            async with async_timeout.timeout(10):
                # Note: asyncio.TimeoutError and aiohttp.ClientError are already
                # handled by the DataUpdateCoordinator base class.

                if self._connected is False:
                    # Create the cookies required for further methods
                    await self._hass.async_add_executor_job(
                        self._p1xx.handshake
                    )
                    # Send credentials to the plug and create AES Key and IV for further methods
                    await self._hass.async_add_executor_job(
                        self._p1xx.login
                    )
                    self._connected = True # omit handshake/loging until any error occurs

                # get device name
                device_name: Final[str] = await self._hass.async_add_executor_job(
                    self._p1xx.getDeviceName
                )
                data[COORDINATOR_DATA_KEY_NAME] = device_name

                # get device info
                device_info: Final[dict[str, Any]] = await self._hass.async_add_executor_job(
                    self._p1xx.getDeviceInfo
                )
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug("getDeviceInfo: %s", device_info)
                data[COORDINATOR_DATA_KEY_DEVICEINFO] = device_info["result"]

                if isinstance(self._p1xx, PyP110.P110):
                    # Only query energy usage, if it is confirmed to be a P110 plug
                    energy_usage: Final[dict[str, Any]] = await self._hass.async_add_executor_job(
                        self._p1xx.getEnergyUsage
                    )
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug("getEnergyUsage: %s", energy_usage)
                    data[COORDINATOR_DATA_KEY_ENERGY] = energy_usage["result"]

                # return data to DataUpdateCoordinator,
                # where it is accessible via 'coordinator.data'
                return data

            _LOGGER.debug("_async_update_data: timeout")

        except Exception as err: # pylint: disable=broad-except
            _LOGGER.warning("_async_update_data: Exception: %s", err)
            self._connected = False # repeat handshake/login
            # Force CoordinatorEntity to forget any previous data
            self.data = {}
            # UpdateFailed will trigger HA to do retries
            raise UpdateFailed from err

    @property
    def unique_id(self) -> str | None:
        """Return a unique_id."""
        return self._config_entry_unique_id

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""

        if not self.data:
            return None

        device_name = self.data[COORDINATOR_DATA_KEY_NAME]
        device_unique_id = self.data[COORDINATOR_DATA_KEY_DEVICEINFO]["device_id"]
        device_fw_version = self.data[COORDINATOR_DATA_KEY_DEVICEINFO]["fw_ver"]
        device_model = self.data[COORDINATOR_DATA_KEY_DEVICEINFO]["model"]

        return DeviceInfo(
            identifiers = {(DOMAIN, device_unique_id)},
            default_name = device_name,
            default_manufacturer = MANUFACTURER,
            default_model = device_model,
            sw_version = device_fw_version,
            via_device = (DOMAIN, self._config_entry_unique_id),
            configuration_url = TAPOCLOUD_URL
        )
