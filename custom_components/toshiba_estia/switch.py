"""Switch platform for the Toshiba Estia integration."""
from __future__ import annotations

import logging

from toshiba_estia.device import ToshibaAcDevice

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import ToshibaAcStateEntity
from .estia_compat import set_hot_water_booster

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add switch entities for passed config entry in HA."""
    device_manager = hass.data[DOMAIN][config_entry.entry_id]
    new_entities = []

    devices: list[ToshibaAcDevice] = await device_manager.get_devices()
    for device in devices:
        new_entities.append(ToshibaDHWBoosterSwitch(device))

    if new_entities:
        _LOGGER.info("Adding %d %s", len(new_entities), "switches")
        async_add_devices(new_entities)


class ToshibaDHWBoosterSwitch(ToshibaAcStateEntity, SwitchEntity):
    """DHW electric booster request switch."""

    _attr_has_entity_name = True
    _attr_name = "Hot water booster"
    _attr_translation_key = "dhw_booster"
    _attr_icon = "mdi:water-boiler"

    def __init__(self, device: ToshibaAcDevice) -> None:
        """Initialize booster switch."""
        super().__init__(device)
        self._attr_unique_id = f"{device.ac_unique_id}_dhw_booster"

    def _raw_byte(self, one_based_index: int) -> int | None:
        raw = getattr(self._device.fcu_state, "_status_string", "")
        start = (one_based_index - 1) * 2
        end = start + 2
        if len(raw) < end:
            return None
        try:
            return int(raw[start:end], 16)
        except ValueError:
            return None

    @property
    def is_on(self) -> bool | None:
        """Return if DHW booster is currently requested."""
        b10 = self._raw_byte(10)
        b19 = self._raw_byte(19)
        return bool(
            (b10 is not None and (b10 & 0x10))
            or (b19 is not None and (b19 & 0x10))
            or self._device.electric_coil_dhw_is_active
        )

    async def async_turn_on(self, **kwargs):
        """Request DHW booster ON."""
        await set_hot_water_booster(self._device, True)

    async def async_turn_off(self, **kwargs):
        """Request DHW booster OFF."""
        await set_hot_water_booster(self._device, False)
