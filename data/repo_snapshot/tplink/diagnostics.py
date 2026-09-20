

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from . import TPLinkConfigEntry

TO_REDACT = {

    "unique_id",

    "alias",
    "mac",
    "mic_mac",
    "host",
    "hwId",
    "oemId",
    "deviceId",
    "id",

    "latitude",
    "latitude_i",
    "longitude",
    "longitude_i",

    "username",

    "device_id",
    "hw_id",
    "fw_id",
    "oem_id",
    "ssid",
    "nickname",
    "ip",

    "original_device_id",
    "parent_device_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TPLinkConfigEntry
) -> dict[str, Any]:

    data = entry.runtime_data
    coordinator = data.parent_coordinator
    oui = format_mac(coordinator.device.mac)[:8].upper()
    return async_redact_data(
        {"device_last_response": coordinator.device.internal_state, "oui": oui},
        TO_REDACT,
    )
