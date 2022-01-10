"""Config flow for TP-Link Tapo integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Final
import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant import (
    config_entries,
    exceptions,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from PyP100 import PyP100

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA: Final = vol.Schema({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_HOST): cv.string,
})

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user inputs."""

    # 'data' has the keys from DATA_SCHEMA with values provided by the user.
    host: Final[str] = data[CONF_HOST]
    login: Final[str] = data[CONF_USERNAME]
    password: Final[str] = data[CONF_PASSWORD]

    # Validate user's input before attempting to use them in a test connection
    # do not log password
    _LOGGER.debug("validate_input:enter: %s=%s %s=%s", CONF_HOST, host, CONF_USERNAME, login)

    if len(host) < 3:
        # Hostname or IP-address with less than 3 characters seems wrong
        _LOGGER.warning("validate_input: Too short: %s=%s", CONF_HOST, host)
        raise InvalidHost
    if len(login) < 1:
        # empty username
        _LOGGER.warning("validate_input: Too short: %s=%s", CONF_USERNAME, login)
        raise InvalidUsername

    # List all devices
    try:
        device_list = await hass.async_add_executor_job(
            PyP100.getDeviceList, login, password
        )
        _LOGGER.debug("getDeviceList: %s", device_list)
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("validate_input: getDeviceList Exception: %s", err)
        # not raising any Exception

    # Setting up a test connection with device/cloud
    p100: Final = PyP100.P100(host, login, password)

    # Create the cookies required for further methods
    try:
        await hass.async_add_executor_job(
            p100.handshake
        )
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("validate_input: handshake Exception: %s", err)
        raise CannotConnect from err

    # Send credentials to the plug and create AES Key and IV for further methods
    try:
        await hass.async_add_executor_job(
            p100.login
        )
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("validate_input: login Exception: %s", err)
        raise InvalidAuth from err

    # Retrieve device name
    try:
        device_name: Final[str] = await hass.async_add_executor_job(
            p100.getDeviceName
        )
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("validate_input: getDeviceName Exception: %s", err)
        raise CannotCommunicate from err

    # Retrieve device model
    try:
        device_info: str = await hass.async_add_executor_job(
            p100.getDeviceInfo
        )
        device_model: Final[str] = device_info["result"]["model"]
    except Exception as err: # pylint: disable=broad-except
        _LOGGER.warning("validate_input: getDeviceInfo Exception: %s", err)
        raise CannotCommunicate from err

    # Return device_name with key 'title', User will see this string in success dialog.
    # Add model with key 'model', which is used in __init__.async_setup_entry().
    info: Final[dict[str, Any]] = {"title": f"{device_model} {device_name}", "model": device_model}
    _LOGGER.debug("validate_input:exit: info=%s", info)
    return info


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TP-Link Tapo."""

    VERSION: Final = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a config flow initiated by the user."""

        # do not log user_input because it contains a password
        _LOGGER.debug("async_step_user:enter")

        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                info: Final[dict[str, Any]] = await validate_input(self.hass, user_input)
                # Adding the device model detected by validate_input.
                # This is then also passed into __init__.async_setup_entry
                user_input["model"] = info["model"]
                return self.async_create_entry(title=info["title"], data=user_input)

            # Error messages are shown next to the input item denoted with CONF_...
            # The error texts are defined in folder translations.
            except InvalidHost:
                errors[CONF_HOST] = "invalid_host"
            except InvalidUsername:
                errors[CONF_USERNAME] = "invalid_username"
            except CannotConnect:
                errors[CONF_HOST] = "cannot_connect"
            except InvalidAuth:
                errors[CONF_USERNAME] = "invalid_auth"
            except CannotCommunicate:
                errors[CONF_HOST] = "cannot_communicate"
            # catch whatever might have gone wrong elsewhere
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                # "base" brings up the message for the full form
                errors["base"] = "unknown_error"

        # If there is no user input or there were errors, show the form again,
        # including any errors that were found with the input.
        _LOGGER.debug("async_step_user:exit: errors=%s", errors)

        return self.async_show_form(
            step_id = "user", data_schema = DATA_SCHEMA, errors = errors
        )


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""

class InvalidUsername(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid username."""

class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is an authentication failure."""

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate there is a connection issue."""

class CannotCommunicate(exceptions.HomeAssistantError):
    """Error to indicate there is a communication failure."""
