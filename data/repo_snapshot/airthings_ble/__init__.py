

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import MAX_RETRIES_AFTER_STARTUP
from .coordinator import AirthingsBLEConfigEntry, AirthingsBLEDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: AirthingsBLEConfigEntry
) -> bool:

    coordinator = AirthingsBLEDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()





    coordinator.airthings.set_max_attempts(MAX_RETRIES_AFTER_STARTUP)

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AirthingsBLEConfigEntry
) -> bool:

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
