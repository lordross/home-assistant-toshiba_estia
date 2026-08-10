"""Config flow for Toshiba AC integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from toshiba_estia.device_manager import ToshibaAcDeviceManager
from toshiba_estia.utils.http_api import ToshibaAcHttpApiAuthError, ToshibaAcHttpApiError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ZONE1_MAX_TEMP,
    CONF_ZONE1_MIN_TEMP,
    CONF_ZONE2_MAX_TEMP,
    CONF_ZONE2_MIN_TEMP,
    DEFAULT_ZONE_MAX_TEMP,
    DEFAULT_ZONE_MIN_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    device_id = f"{random.getrandbits(64):016x}"

    _LOGGER.debug("Toshiba validate input %s %s", data["username"], device_id)

    device_manager = ToshibaAcDeviceManager(
        data["username"], data["password"], device_id
    )

    try:
        sas_token = await device_manager.connect()

    except ToshibaAcHttpApiAuthError as ex:
        _LOGGER.error("Toshiba connection error %s", ex)
        raise InvalidAuth from ex
    except ToshibaAcHttpApiError as ex:
        _LOGGER.error("Toshiba connection error %s", ex)
        raise CannotConnect from ex
    finally:
        _LOGGER.error("Toshiba connection OK")
        await device_manager.shutdown()

    return {
        "username": data["username"],
        "password": data["password"],
        "device_id": device_id,
        "sas_token": sas_token,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Toshiba AC."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow."""
        return ToshibaOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            data = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=user_input["username"], data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ToshibaOptionsFlow(config_entries.OptionsFlow):
    """Handle Toshiba options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            if user_input[CONF_ZONE1_MIN_TEMP] > user_input[CONF_ZONE1_MAX_TEMP]:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(user_input),
                    errors={"base": "zone1_invalid_range"},
                )
            if user_input[CONF_ZONE2_MIN_TEMP] > user_input[CONF_ZONE2_MAX_TEMP]:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(user_input),
                    errors={"base": "zone2_invalid_range"},
                )
            return self.async_create_entry(
                title="",
                data={
                    CONF_ZONE1_MIN_TEMP: int(user_input[CONF_ZONE1_MIN_TEMP]),
                    CONF_ZONE1_MAX_TEMP: int(user_input[CONF_ZONE1_MAX_TEMP]),
                    CONF_ZONE2_MIN_TEMP: int(user_input[CONF_ZONE2_MIN_TEMP]),
                    CONF_ZONE2_MAX_TEMP: int(user_input[CONF_ZONE2_MAX_TEMP]),
                },
            )

        options = self.config_entry.options
        defaults = {
            CONF_ZONE1_MIN_TEMP: int(
                options.get(CONF_ZONE1_MIN_TEMP, DEFAULT_ZONE_MIN_TEMP)
            ),
            CONF_ZONE1_MAX_TEMP: int(
                options.get(CONF_ZONE1_MAX_TEMP, DEFAULT_ZONE_MAX_TEMP)
            ),
            CONF_ZONE2_MIN_TEMP: int(
                options.get(CONF_ZONE2_MIN_TEMP, DEFAULT_ZONE_MIN_TEMP)
            ),
            CONF_ZONE2_MAX_TEMP: int(
                options.get(CONF_ZONE2_MAX_TEMP, DEFAULT_ZONE_MAX_TEMP)
            ),
        }
        return self.async_show_form(step_id="init", data_schema=self._schema(defaults))

    @staticmethod
    def _schema(current: dict[str, int]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_ZONE1_MIN_TEMP, default=current[CONF_ZONE1_MIN_TEMP]): vol.All(
                    vol.Coerce(int), vol.Range(min=7, max=40)
                ),
                vol.Required(CONF_ZONE1_MAX_TEMP, default=current[CONF_ZONE1_MAX_TEMP]): vol.All(
                    vol.Coerce(int), vol.Range(min=7, max=40)
                ),
                vol.Required(CONF_ZONE2_MIN_TEMP, default=current[CONF_ZONE2_MIN_TEMP]): vol.All(
                    vol.Coerce(int), vol.Range(min=7, max=40)
                ),
                vol.Required(CONF_ZONE2_MAX_TEMP, default=current[CONF_ZONE2_MAX_TEMP]): vol.All(
                    vol.Coerce(int), vol.Range(min=7, max=40)
                ),
            }
        )
