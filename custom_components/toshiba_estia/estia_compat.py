"""Compatibility helpers for Estia control across library versions."""
from __future__ import annotations

import datetime as dt
import json
import time
import asyncio
import logging

from homeassistant.components.climate.const import HVACMode
from homeassistant.components.water_heater.const import (
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
)
from toshiba_estia.device import ToshibaAcDevice, ToshibaAcStatus
from toshiba_estia.device.properties import ToshibaAcMode

_LOGGER = logging.getLogger(__name__)
STATE_OFF = "off"
ZONE_MIN_TEMP = 16
ZONE_MAX_TEMP = 40


def _water_function_is_on(device: ToshibaAcDevice) -> bool:
    return _raw_byte(device, 5) == 0x03


def _dhw_is_on(device: ToshibaAcDevice) -> bool:
    return _raw_byte(device, 1) == 0x0C


def _dhw_booster_is_on(device: ToshibaAcDevice) -> bool:
    b10 = _raw_byte(device, 10) or 0
    b19 = _raw_byte(device, 19) or 0
    return bool((b10 & 0x10) or (b19 & 0x10) or device.electric_coil_dhw_is_active)


def _temp_to_raw(temp_c: int) -> int:
    return int(temp_c * 2 + 32)


def _source_id(device: ToshibaAcDevice) -> str:
    if "_" in device.device_id:
        return device.device_id.split("_", 1)[1]
    return device.device_id


def _timestamp_7() -> str:
    return dt.datetime.now().strftime("%H:%M:%S.%f") + "0"


def _payload_14(changes: dict[int, int]) -> str:
    data = [0xFF] * 14
    for idx, val in changes.items():
        if 1 <= idx <= 14:
            data[idx - 1] = val & 0xFF
    return "".join(f"{b:02x}" for b in data)


def _raw_byte(device: ToshibaAcDevice, one_based_index: int) -> int | None:
    raw = getattr(device.fcu_state, "_status_string", "")
    start = (one_based_index - 1) * 2
    end = start + 2
    if len(raw) < end:
        return None
    try:
        return int(raw[start:end], 16)
    except ValueError:
        return None


async def _send_hdu(device: ToshibaAcDevice, changes: dict[int, int]) -> None:
    source = _source_id(device)
    message = {
        "timeStamp": _timestamp_7(),
        "messageId": f"MB_{source}-{int(time.time() * 1000) % 100000000:08d}",
        "sourceId": source,
        "targetId": [device.ac_unique_id],
        "cmd": "CMD_HDU_TO_ESTIA",
        "payload": {"data": _payload_14(changes)},
    }
    payload = json.dumps(message)
    try:
        await device.amqp_api.send_message(payload)
    except Exception as err:
        # Azure client can occasionally drop the pipeline between commands.
        # Reconnect AMQP once and retry the same frame.
        if "Pipeline is not running" not in str(err):
            raise
        _LOGGER.warning("AMQP pipeline not running, reconnecting and retrying control frame")
        await device.amqp_api.connect()
        await device.amqp_api.send_message(payload)


async def _refresh_zone_state(device: ToshibaAcDevice) -> None:
    """Reload FCU state so byte checks use fresh telemetry."""
    try:
        await device.state_reload()
    except Exception:
        # Keep command flow resilient even if immediate refresh fails.
        pass


async def set_zone_temperature(device: ToshibaAcDevice, zone: int, temp_c: int) -> None:
    bounded = max(ZONE_MIN_TEMP, min(ZONE_MAX_TEMP, int(temp_c)))
    await _send_hdu(device, {7 if zone == 1 else 14: _temp_to_raw(bounded)})


def _active_mode_raw(device: ToshibaAcDevice) -> int:
    mode = _raw_byte(device, 6)
    if mode in (0x05, 0x06):
        return mode
    if getattr(device, "mode", None) == ToshibaAcMode.COOL:
        return 0x05
    return 0x06


def _zone1_raw(device: ToshibaAcDevice) -> int:
    return _temp_to_raw(int(device.zone1_target_temperature or 21))


async def _ensure_enabled(device: ToshibaAcDevice, mode_raw: int) -> None:
    # Most firmwares start circulation only when mode+target are written together.
    await _send_hdu(device, {4: mode_raw, 7: _zone1_raw(device)})
    await asyncio.sleep(1.0)
    await _refresh_zone_state(device)
    if _water_function_is_on(device):
        return

    # Retry same app-like command once.
    await _send_hdu(device, {4: mode_raw, 7: _zone1_raw(device)})
    await asyncio.sleep(1.0)
    await _refresh_zone_state(device)
    if _water_function_is_on(device):
        return

    # Fallback for units that need explicit zone-enable before mode write.
    await _send_hdu(device, {3: 0x03})
    await asyncio.sleep(1.0)
    await _refresh_zone_state(device)
    await _send_hdu(device, {4: mode_raw, 7: _zone1_raw(device)})
    await asyncio.sleep(1.0)
    await _refresh_zone_state(device)


async def set_hvac_mode(device: ToshibaAcDevice, hvac_mode: HVACMode) -> None:
    if hvac_mode == HVACMode.COOL:
        ac_mode = ToshibaAcMode.COOL
        mode_raw = 0x05
    elif hvac_mode == HVACMode.HEAT:
        ac_mode = ToshibaAcMode.HEAT
        mode_raw = 0x06
    else:
        ac_mode = ToshibaAcMode.AUTO
        mode_raw = None

    if mode_raw is not None:
        await _ensure_enabled(device, mode_raw)
        return

    # AUTO fallback for versions that may support it.
    if hasattr(device, "set_ac_mode"):
        await device.set_ac_mode(ac_mode)


async def set_dhw_temperature(device: ToshibaAcDevice, temp_c: int) -> None:
    await _send_hdu(device, {2: _temp_to_raw(int(temp_c))})


async def set_dhw_enabled(device: ToshibaAcDevice, enabled: bool) -> None:
    await _send_hdu(device, {1: 0x0C if enabled else 0x08})


async def set_hot_water_booster(device: ToshibaAcDevice, enabled: bool) -> None:
    await _send_hdu(device, {10: 0x10 if enabled else 0x00})


async def set_dhw_operation_mode(device: ToshibaAcDevice, operation_mode: str) -> None:
    if operation_mode == STATE_OFF:
        await set_hot_water_booster(device, False)
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        await set_dhw_enabled(device, False)
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        if _dhw_is_on(device):
            await set_dhw_enabled(device, False)
            await asyncio.sleep(0.6)
            await _refresh_zone_state(device)
        return

    await set_dhw_enabled(device, True)
    await asyncio.sleep(0.6)
    await _refresh_zone_state(device)
    if not _dhw_is_on(device):
        await set_dhw_enabled(device, True)
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)

    if operation_mode == STATE_ELECTRIC:
        await set_hot_water_booster(device, True)
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        if not _dhw_booster_is_on(device):
            await set_hot_water_booster(device, True)
            await asyncio.sleep(0.6)
            await _refresh_zone_state(device)
        return

    if operation_mode == STATE_HEAT_PUMP:
        await set_hot_water_booster(device, False)
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        if _dhw_booster_is_on(device):
            await set_hot_water_booster(device, False)
            await asyncio.sleep(0.6)
            await _refresh_zone_state(device)
        return

    raise ValueError(f"Unsupported DHW operation mode: {operation_mode}")


async def set_zones_enabled(device: ToshibaAcDevice, enabled: bool) -> None:
    if enabled:
        await _ensure_enabled(device, _active_mode_raw(device))
    else:
        # OFF mapping has been observed inverted on some units/firmwares.
        # Try app-captured alternate OFF candidate first, then classic 0x02.
        await _send_hdu(device, {3: 0x03})
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        if not _water_function_is_on(device):
            return
        await _send_hdu(device, {3: 0x02})
        await asyncio.sleep(0.6)
        await _refresh_zone_state(device)
        if not _water_function_is_on(device):
            return

        # Prefer native status command when available in pinned library.
        if hasattr(device, "set_ac_status"):
            await device.set_ac_status(ToshibaAcStatus.OFF)
            await asyncio.sleep(0.6)
            await _refresh_zone_state(device)
            if not _water_function_is_on(device):
                return
        # Final fallback: force OFF water function flag for strict firmwares.
        await _send_hdu(device, {3: 0x02, 5: 0x00})
