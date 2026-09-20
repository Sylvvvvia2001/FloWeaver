

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .bridge import HueConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HueConfigEntry
) -> dict[str, Any]:

    bridge = entry.runtime_data
    if bridge.api_version == 1:

        return {}

    return await bridge.api.get_diagnostics()
