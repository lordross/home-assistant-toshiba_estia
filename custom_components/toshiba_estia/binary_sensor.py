"""Platform for sensor integration."""
from __future__ import annotations

from datetime import date, datetime
import logging

from toshiba_estia.device import ToshibaAcDevice

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,

)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfVolumeFlowRate
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .entity import ToshibaAcEntity, ToshibaAcStateEntity

_LOGGER = logging.getLogger(__name__)

#@dataclass
class HABinarySensor:
    name: str
    value: str
    translation_key: str
    device_class: BinarySensorDeviceClass

    def __init__(self, name : str, value : str, device_class : BinarySensorDeviceClass):
        self.name = name
        self.value =  value
        self.translation_key = value
        self.device_class = device_class

temperature_sensors_array = [
    HABinarySensor(name = "Water Pump", value = "water_pump_status", device_class=BinarySensorDeviceClass.RUNNING),
    HABinarySensor(name = "Heat Electric Heater", value = "electric_coil_heat_is_active", device_class=BinarySensorDeviceClass.POWER),
    HABinarySensor(name = "DHW Electric Heater", value = "electric_coil_dhw_is_active", device_class=BinarySensorDeviceClass.POWER),
]



# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensor for passed config_entry in HA."""
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    device_manager = hass.data[DOMAIN][config_entry.entry_id]

    # The next few lines find all of the entities that will need to be added
    # to HA. Note these are all added to a list, so async_add_devices can be
    # called just once.
    new_devices = []

    devices: list[ToshibaAcDevice] = await device_manager.get_devices()
    for device in devices:
        _LOGGER.debug("device %s", device)

        for sensor in temperature_sensors_array:
            sensor_entity = ToshibaEstiaBinarySensor(sensor, device)
            new_devices.append(sensor_entity)


    # If we have any new devices, add them
    if new_devices:
        _LOGGER.info(f"Adding {len(new_devices)} binary sensors")
        async_add_devices(new_devices)



class ToshibaEstiaBinarySensor(ToshibaAcStateEntity, BinarySensorEntity):
    """Provides a Toshiba Temperature Sensors."""

    _attr_has_entity_name = True

    def __init__(self, parameters : HABinarySensor, device: ToshibaAcDevice):
        """Initialize the sensor."""
        super().__init__(device)
        self.init_parameters = parameters
        self._attr_name = parameters.name
        self._attr_device_class = parameters.device_class
        self._attr_unique_id = f"{device.ac_unique_id}_{parameters.value}_binary_sensor"
        self._attr_translation_key = parameters.translation_key

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""

        if getattr(self._device, self.init_parameters.value) is None:
            return False

        if self.init_parameters.value == -24:
            return False

        return super().available

    @property
    def is_on(self) -> bool() | None:
        """Return the value reported by the sensor."""
        return getattr(self._device, self.init_parameters.value)
