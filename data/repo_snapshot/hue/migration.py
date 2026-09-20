

import logging

from aiohue import HueBridgeV2
from aiohue.discovery import is_v2_bridge
from aiohue.v2.models.device import DeviceArchetypes
from aiohue.v2.models.resource import ResourceTypes

from homeassistant import core
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_API_KEY, CONF_API_VERSION, CONF_HOST, CONF_USERNAME
from homeassistant.helpers import (
    aiohttp_client,
    device_registry as dr,
    entity_registry as er,
)

from .bridge import HueConfigEntry
from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


async def check_migration(hass: core.HomeAssistant, entry: HueConfigEntry) -> None:

    host = entry.data[CONF_HOST]


    if CONF_USERNAME in entry.data:
        LOGGER.info("Migrate %s to %s in schema", CONF_USERNAME, CONF_API_KEY)
        data = dict(entry.data)
        data[CONF_API_KEY] = data.pop(CONF_USERNAME)
        hass.config_entries.async_update_entry(entry, data=data)

    if (conf_api_version := entry.data.get(CONF_API_VERSION, 1)) == 1:


        websession = aiohttp_client.async_get_clientsession(hass)
        if await is_v2_bridge(host, websession):
            supported_api_version = 2
        else:
            supported_api_version = 1
        LOGGER.debug(
            "Configured api version is %s and supported api version %s for bridge %s",
            conf_api_version,
            supported_api_version,
            host,
        )




        if conf_api_version == 1 and supported_api_version == 2:

            await handle_v2_migration(hass, entry)


        if (
            CONF_API_VERSION not in entry.data
            or conf_api_version != supported_api_version
        ):
            data = dict(entry.data)
            data[CONF_API_VERSION] = supported_api_version
            hass.config_entries.async_update_entry(entry, data=data)


async def handle_v2_migration(hass: core.HomeAssistant, entry: HueConfigEntry) -> None:

    host = entry.data[CONF_HOST]
    api_key = entry.data[CONF_API_KEY]
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    LOGGER.info("Start of migration of devices and entities to support API schema 2")




    dev_ids = {}
    for hass_dev in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        for domain, mac in hass_dev.identifiers:
            if domain != DOMAIN:
                continue
            normalized_mac = mac.split("-")[0]
            dev_ids[normalized_mac] = hass_dev.id


    async with HueBridgeV2(host, api_key) as api:
        sensor_class_mapping = {
            SensorDeviceClass.BATTERY.value: ResourceTypes.DEVICE_POWER,
            BinarySensorDeviceClass.MOTION.value: ResourceTypes.MOTION,
            SensorDeviceClass.ILLUMINANCE.value: ResourceTypes.LIGHT_LEVEL,
            SensorDeviceClass.TEMPERATURE.value: ResourceTypes.TEMPERATURE,
        }


        for hue_dev in api.devices:
            zigbee = api.devices.get_zigbee_connectivity(hue_dev.id)
            if not zigbee or not zigbee.mac_address:

                continue


            if hue_dev.product_data.product_archetype == DeviceArchetypes.BRIDGE_V2:
                hass_dev_id = dev_ids.get(api.config.bridge_id.upper())
            else:
                hass_dev_id = dev_ids.get(zigbee.mac_address)
            if hass_dev_id is None:

                LOGGER.debug(
                    (
                        "Ignoring device %s (%s) as it does not (yet) exist in the"
                        " device registry"
                    ),
                    hue_dev.metadata.name,
                    hue_dev.id,
                )
                continue
            dev_reg.async_update_device(
                hass_dev_id, new_identifiers={(DOMAIN, hue_dev.id)}
            )
            LOGGER.info("Migrated device %s (%s)", hue_dev.metadata.name, hass_dev_id)


            for ent in er.async_entries_for_device(ent_reg, hass_dev_id, True):
                if ent.entity_id.startswith("light"):


                    new_unique_id = next(iter(hue_dev.lights), None)
                else:

                    matched_dev_class = sensor_class_mapping.get(
                        ent.original_device_class or "unknown"
                    )
                    new_unique_id = next(
                        (
                            sensor.id
                            for sensor in api.devices.get_sensors(hue_dev.id)
                            if sensor.type == matched_dev_class
                        ),
                        None,
                    )

                if new_unique_id is None:

                    LOGGER.warning(
                        (
                            "Skip migration of %s because it no longer exists on the"
                            " bridge"
                        ),
                        ent.entity_id,
                    )
                    continue

                try:
                    ent_reg.async_update_entity(
                        ent.entity_id, new_unique_id=new_unique_id
                    )
                except ValueError:



                    LOGGER.warning(
                        "Skip migration of %s because it already exists",
                        ent.entity_id,
                    )
                else:
                    LOGGER.info(
                        "Migrated entity %s from unique id %s to %s",
                        ent.entity_id,
                        ent.unique_id,
                        new_unique_id,
                    )


        for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if ent.device_id is not None:
                continue
            if "-" in ent.unique_id:

                hue_group = api.groups.get(ent.unique_id)
            else:

                v1_id = f"/groups/{ent.unique_id}"
                hue_group = api.groups.room.get_by_v1_id(
                    v1_id
                ) or api.groups.zone.get_by_v1_id(v1_id)
            if hue_group is None or hue_group.grouped_light is None:

                LOGGER.warning(
                    "Skip migration of %s because it no longer exist on the bridge",
                    ent.entity_id,
                )
                continue
            new_unique_id = hue_group.grouped_light
            LOGGER.info(
                "Migrating %s from unique id %s to %s ",
                ent.entity_id,
                ent.unique_id,
                new_unique_id,
            )
            try:
                ent_reg.async_update_entity(ent.entity_id, new_unique_id=new_unique_id)
            except ValueError:



                LOGGER.warning(
                    "Skip migration of %s because it already exists",
                    ent.entity_id,
                )
    LOGGER.info("Migration of devices and entities to support API schema 2 finished")
