"""TP-Link Tapo Cloud Integration"""

from __future__ import annotations

import sys
from datetime import timedelta
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from PyP100 import PyP100, PyP110

from .const import DOMAIN
from .tapo_coordinator import TapoDataUpdateCoordinator

MIN_PYTHON = (3, 9) # was tested only with 3.9
if sys.version_info < MIN_PYTHON:
    sys.exit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or later is required.\n")


SCAN_INTERVAL: Final[timedelta] = timedelta(seconds=30)

# List of platforms to support.
PLATFORMS: list[str] = [
#    Platform.LIGHT,
    Platform.SENSOR,
#    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tapo device from a config entry."""

    _LOGGER.debug("async_setup_entry:enter: entry.entry_id=%s", entry.entry_id)

    # Setup connection with device/cloud
    #
    # Only valid configuration comes in here, no need for validation
    host: str = entry.data[CONF_HOST]
    username: str = entry.data.get(CONF_USERNAME)
    password: str = entry.data.get(CONF_PASSWORD)
    # model was added in config_flow.async_step_user
    device_model: str = entry.data.get("model")

    if device_model == "P110":
        p1xx = PyP110.P110(host, username, password)
    else:
        p1xx = PyP100.P100(host, username, password)

    # Create coordinator that does the work of speaking with the actual devices.
    coordinator = TapoDataUpdateCoordinator(
        hass,
        p1xx,
        interval = SCAN_INTERVAL,
        config_entry_unique_id = entry.unique_id
    )

    # Fetch initial data so we have data when entities subscribe
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later.
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    await coordinator.async_config_entry_first_refresh()

    # Store the instance of the TapoDataUpdateCoordinator class,
    # so that entities can access the data fetched from the coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # This creates each HA object for each platform the device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    _LOGGER.debug("async_setup_entry:exit: entry.entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.debug("async_unload_entry:enter: entry.entry_id=%s", entry.entry_id)

    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    _LOGGER.debug("async_unload_entry:exit: unload_ok=%s entry.entry_id=%s",
                  unload_ok, entry.entry_id)
    return unload_ok
