"""Platform for climate integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from toshiba_estia.device import (
    ToshibaAcDevice,
    EstiaWaterMode,
    ToshibaAcStatus,
)
from toshiba_estia.utils import pretty_enum_name

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .entity import ToshibaAcStateEntity
from .feature_list import get_feature_by_name, get_feature_list

_LOGGER = logging.getLogger(__name__)

TOSHIBA_TO_HVAC_MODE = {
    EstiaWaterMode.AUTO: HVACMode.AUTO,
    EstiaWaterMode.COOL: HVACMode.COOL,
    EstiaWaterMode.HEAT: HVACMode.HEAT,
}

HVAC_MODE_TO_TOSHIBA = {v: k for k, v in TOSHIBA_TO_HVAC_MODE.items()}


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add climate for passed config_entry in HA."""
    device_manager = hass.data[DOMAIN][config_entry.entry_id]
    new_entities = []

    _LOGGER.info("Registering climate entries")

    try:
        devices = await device_manager.get_devices()
        for device in devices:
            climate_entity = ToshibaHeatingZone(device)
            new_entities.append(climate_entity)
    except Exception as ex:
        _LOGGER.error("Error during connection to Toshiba server %s", ex)
        raise ConfigEntryNotReady("Error during connection to Toshiba server") from ex

    if new_entities:
        _LOGGER.info("Adding %d %s", len(new_entities), "climates")
        async_add_devices(new_entities)


class ToshibaHeatingZone(ToshibaAcStateEntity, ClimateEntity):
    """Provides a Toshiba climates."""

    # This is the main entity for the device
    _attr_has_entity_name = True
    _attr_name = None

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, toshiba_device: ToshibaAcDevice):
        """Initialize the climate."""
        super().__init__(toshiba_device)

        self._enable_turn_on_off_backwards_compatibility = False
        self._attr_unique_id = f"{self._device.ac_unique_id}_climate"
        self._attr_name = f"{self._device.name} Zone 1"


    @property
    def is_on(self):
        """Return True if the device is on or completely off."""
        return self._device.ac_status == ToshibaAcStatus.ON

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        set_temperature = kwargs[ATTR_TEMPERATURE]
        #TODO: Disabled on purpose
        #await self._device.set_ac_temperature(set_temperature)

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._device.set_ac_status(ToshibaAcStatus.ON)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self._device.set_ac_status(ToshibaAcStatus.OFF)

    async def async_toggle(self) -> None:
        """Toggle device status."""
        state = self._device.ac_status
        if state == ToshibaAcStatus.OFF:
            await self.async_turn_on()
        else:
            await self.async_turn_off()

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return hvac operation ie. heat, cool mode."""
        current_hvac_mode = self._device.mode

        return TOSHIBA_TO_HVAC_MODE[current_hvac_mode]

    @property
    def hvac_modes(self) -> list[HVACMode] | list[str]:
        """Return the list of available hvac operation modes."""
        available_modes = [HVACMode.OFF]
        available_modes.append(HVACMode.HEAT)
        available_modes.append(HVACMode.COOL)
        available_modes.append(HVACMode.AUTO)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        _LOGGER.info("Toshiba Climate setting hvac_mode: %s", hvac_mode)

        if hvac_mode == HVACMode.OFF:
            await self._device.set_ac_status(ToshibaAcStatus.OFF)
        else:
            if not self.is_on:
                await self._device.set_ac_status(ToshibaAcStatus.ON)
            await self._device.set_ac_mode(HVAC_MODE_TO_TOSHIBA[hvac_mode])


    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._device.zone1_target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 20

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 40

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        return {
            "outdoor_temperature": self._device.temperatures.to,
        }
