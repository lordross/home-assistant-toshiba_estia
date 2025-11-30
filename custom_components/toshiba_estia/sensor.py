"""Platform for sensor integration."""
from __future__ import annotations

from datetime import date, datetime
import logging

from toshiba_estia.device import ToshibaAcDevice, ToshibaAcDeviceEnergyConsumption

from toshiba_estia.device.properties import (
    ToshibaAcDeviceEnergyConsumption,
    ToshibaAcMode,
    ToshibaAcStatus,
    EstiaCompressorStatus,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfVolumeFlowRate
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .entity import ToshibaAcEntity, ToshibaAcStateEntity

_LOGGER = logging.getLogger(__name__)

COMPRESSOR_STATUS_OPTIONS = [
    "Off",
    "Hot Water",
    "Heat",
]

COMPRESSOR_STATUS_TO_MODE_STRING = {
    EstiaCompressorStatus.OFF: "Off",
    EstiaCompressorStatus.DHW: "Hot Water",
    EstiaCompressorStatus.HEAT: "Heat",
}


#@dataclass
class HASensor:
    value: str
    translation_key: str

    def __init__(self, value : str, translation_key : str):
        self.value =  value
        self.translation_key = translation_key

class HASensorEnum:
    value: str
    translation_key: str
    options: list[str]

    def __init__(self, value : str, translation_key : str, options: list[str]):
        self.value =  value
        self.translation_key = translation_key
        self.options = options

temperature_sensors_array = [
    HASensor(value = "dhw_target_temperature", translation_key = "dhw_target_temperature"),
    HASensor(value = "twi_temperature", translation_key = "twi_temperature"),
    HASensor(value = "two_temperature", translation_key = "two_temperature"),
    HASensor(value = "tho_temperature", translation_key = "tho_temperature"),
    HASensor(value = "to_temperature", translation_key = "to_temperature"),
    HASensor(value = "tfi_temperature", translation_key = "tfi_temperature")
]

flow_sensors_array = [
    HASensor(value = "water_flow_rate", translation_key = "water_flow_rate"),
]


enum_sensors_array = [
    HASensorEnum(value = "compressor_status", translation_key = "compressor_status", options=COMPRESSOR_STATUS_OPTIONS),
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
        _LOGGER.debug(f"Adding sensors for device '{device}'")

        for sensor in temperature_sensors_array:
            sensor_entity = ToshibaTempSensor(sensor, device)
            new_devices.append(sensor_entity)

        for sensor in flow_sensors_array:
            sensor_entity = ToshibaFlowSensor(sensor, device)
            new_devices.append(sensor_entity)

        for sensor in enum_sensors_array:
            sensor_entity = ToshibaEnumSensor(sensor, device)
            new_devices.append(sensor_entity)

        new_devices.append(ToshibaPowerSensor(device))

    # If we have any new devices, add them
    if new_devices:
        _LOGGER.info("Adding %d %s", len(new_devices), "sensors")
        async_add_devices(new_devices)


class ToshibaPowerSensor(ToshibaAcEntity, SensorEntity):
    """Provides a Toshiba Sensors."""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _ac_energy_consumption: ToshibaAcDeviceEnergyConsumption | None = None

    def __init__(self, toshiba_device: ToshibaAcDevice):
        """Initialize the sensor."""
        super().__init__(toshiba_device)
        self._attr_unique_id = f"{self._device.ac_unique_id}_sensor"
        self._attr_name = f"{self._device.name} Power Consumption"

    async def state_changed(self, _dev: ToshibaAcDevice):
        """Call if we need to change the ha state."""
        self._ac_energy_consumption = self._device.ac_energy_consumption
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Importantly for a push integration, the module that will be getting updates
        # needs to notify HA of changes. The dummy device has a registercallback
        # method, so to this we add the 'self.async_write_ha_state' method, to be
        # called where ever there are changes.
        # The call back registration is done once this entity is registered with HA
        # (rather than in the __init__)
        # self._device.register_callback(self.async_write_ha_state)
        self._device.on_energy_consumption_changed_callback.add(self.state_changed)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        # self._device.remove_callback(self.async_write_ha_state)
        self._device.on_energy_consumption_changed_callback.remove(self.state_changed)

    @property
    def native_value(self) -> StateType | date | datetime:
        """Return the value reported by the sensor."""
        if self._ac_energy_consumption:
            return self._ac_energy_consumption.energy_wh
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._ac_energy_consumption:
            return {"last_reset": self._ac_energy_consumption.since}
        return {}


class ToshibaTempSensor(ToshibaAcStateEntity, SensorEntity):
    """Provides a Toshiba Temperature Sensors."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, parameters : HASensor, device: ToshibaAcDevice):
        """Initialize the sensor."""
        super().__init__(device)
        self.init_parameters = parameters
        self._attr_unique_id = f"{device.ac_unique_id}_{parameters.value}_sensor"
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
    def native_value(self) -> int | None:
        """Return the value reported by the sensor."""
        return getattr(self._device, self.init_parameters.value)

class ToshibaFlowSensor(ToshibaAcStateEntity, SensorEntity):
    """Provides a Toshiba Temperature Sensors."""

    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.LITERS_PER_MINUTE
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, parameters : HASensor, device: ToshibaAcDevice):
        """Initialize the sensor."""
        super().__init__(device)
        self.init_parameters = parameters
        self._attr_unique_id = f"{device.ac_unique_id}_{parameters.value}_sensor"
        self._attr_translation_key = parameters.translation_key

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""

        if getattr(self._device, self.init_parameters.value) is None:
            return False
        return super().available

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        return getattr(self._device, self.init_parameters.value)


class ToshibaEnumSensor(ToshibaAcStateEntity, SensorEntity):
    """Provides a Toshiba Temperature Sensors."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_has_entity_name = True

    def __init__(self, parameters: HASensorEnum, device: ToshibaAcDevice):
        """Initialize the sensor."""
        super().__init__(device)
        self.init_parameters = parameters
        self._attr_unique_id = f"{device.ac_unique_id}_{parameters.value}_sensor"
        self._attr_translation_key = parameters.translation_key
        self._attr_options = parameters.options
        self._attr_name = "Compressor Status"


    @property
    def available(self) -> bool:
        """Return True if sensor is available."""

        if getattr(self._device, self.init_parameters.value) is None:
            return False

        if self.init_parameters.value == -24:
            return False

        return super().available

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the sensor."""
        state = getattr(self._device, self.init_parameters.value)
        logging.debug(f"Compressor state is: {state}")
        return COMPRESSOR_STATUS_TO_MODE_STRING[(state)]
