

from aiohue.util import normalize_bridge_id

from homeassistant.components import persistent_notification
from homeassistant.config_entries import SOURCE_IGNORE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .bridge import HueBridge, HueConfigEntry
from .const import DOMAIN
from .migration import check_migration
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:


    async_setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: HueConfigEntry) -> bool:


    await check_migration(hass, entry)


    bridge = HueBridge(hass, entry)
    if not await bridge.async_initialize_bridge():
        return False

    api = bridge.api


    unique_id = normalize_bridge_id(api.config.bridge_id)
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(entry, unique_id=unique_id)



    elif entry.unique_id != unique_id:

        other_entry = next(
            (
                entry
                for entry in hass.config_entries.async_entries(DOMAIN)
                if entry.unique_id == unique_id
            ),
            None,
        )
        if other_entry is None:

            hass.config_entries.async_update_entry(entry, unique_id=unique_id)

        elif other_entry.source == SOURCE_IGNORE:

            hass.async_create_task(
                hass.config_entries.async_remove(other_entry.entry_id)
            )
            hass.config_entries.async_update_entry(entry, unique_id=unique_id)
        else:

            hass.async_create_task(hass.config_entries.async_remove(entry.entry_id))
            return False


    device_registry = dr.async_get(hass)
    if bridge.api_version == 1:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, api.config.mac_address)},
            identifiers={(DOMAIN, api.config.bridge_id)},
            manufacturer="Signify",
            name=api.config.name,
            model_id=api.config.model_id,
            sw_version=api.config.software_version,
        )

        if (
            api.config.model_id == "BSB002"
            and api.config.software_version < "1935144040"
        ):
            persistent_notification.async_create(
                hass,
                (
                    "Your Hue hub has a known security vulnerability ([CVE-2020-6007] "
                    "(https://cve.circl.lu/cve/CVE-2020-6007)). "
                    "Go to the Hue app and check for software updates."
                ),
                "Signify Hue",
                "hue_hub_firmware",
            )
    else:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, api.config.mac_address)},
            identifiers={
                (DOMAIN, api.config.bridge_id),
                (DOMAIN, api.config.bridge_device.id),
            },
            manufacturer=api.config.bridge_device.product_data.manufacturer_name,
            name=api.config.name,
            model_id=api.config.model_id,
            sw_version=api.config.software_version,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HueConfigEntry) -> bool:

    return await entry.runtime_data.async_reset()
