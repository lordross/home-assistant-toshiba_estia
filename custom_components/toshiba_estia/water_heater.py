"""Platform for climate integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from toshiba_estia.device import (
    ToshibaAcDevice,
    ToshibaAcMode,
    ToshibaAcStatus,
)
from toshiba_estia.utils import pretty_enum_name

from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.components.water_heater.const import (
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
    STATE_PERFORMANCE,
    STATE_HIGH_DEMAND
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .entity import ToshibaAcStateEntity
from .feature_list import get_feature_by_name, get_feature_list

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add climate for passed config_entry in HA."""
    device_manager = hass.data[DOMAIN][config_entry.entry_id]
    new_entities = []

    _LOGGER.info("Registering water heater entries")

    try:
        devices = await device_manager.get_devices()
        for device in devices:
            new_entities.append(ToshibaDHW(device))
    except Exception as ex:
        _LOGGER.error("Error during connection to Toshiba server %s", ex)
        raise ConfigEntryNotReady("Error during connection to Toshiba server") from ex

    if new_entities:
        _LOGGER.info("Adding %d %s", len(new_entities), "water heaters")
        async_add_devices(new_entities)



class ToshibaDHW(ToshibaAcStateEntity, WaterHeaterEntity):
    """Provides a Toshiba DHW control."""

    # This is the main entity for the device
    _attr_has_entity_name = True
    _attr_name = None

    _attr_supported_features = (
          WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )

    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, toshiba_device: ToshibaAcDevice):
        """Initialize the climate."""
        super().__init__(toshiba_device)

        self._enable_turn_on_off_backwards_compatibility = False
        self._attr_unique_id = f"{self._device.ac_unique_id}_dhw"
        self._attr_name = f"{self._device.name} Hot water"
        self._attr_min_temperature = 20
        self._attr_min_temperature = 65

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        set_temperature = kwargs[ATTR_TEMPERATURE]
#        await self._device.set_ac_temperature(set_temperature)


    async def async_turn_on(self) -> None:
        return None

    async def async_turn_off(self) -> None:
        return None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._device.dhw_target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 20

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 60

    @property
    def current_operation(self) -> str:
        """Return the maximum temperature."""
        if self._device.electric_coil_dhw_is_active == True:
            return STATE_ELECTRIC
        else:
            return STATE_HEAT_PUMP
