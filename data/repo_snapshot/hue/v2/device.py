

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room, Zone
from aiohue.v2.models.device import Device
from aiohue.v2.models.resource import ResourceTypes
from aiohue.v2.models.service_group import ServiceGroup

from homeassistant.const import (
    ATTR_CONNECTIONS,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_MODEL_ID,
    ATTR_NAME,
    ATTR_SUGGESTED_AREA,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from ..const import DOMAIN

if TYPE_CHECKING:
    from ..bridge import HueBridge


async def async_setup_devices(bridge: HueBridge):

    entry = bridge.config_entry
    hass = bridge.hass
    api: HueBridgeV2 = bridge.api
    dev_reg = dr.async_get(hass)
    dev_controller = api.devices

    @callback
    def add_device(hue_resource: Device | Room | Zone | ServiceGroup) -> dr.DeviceEntry:

        if isinstance(hue_resource, (Room, Zone, ServiceGroup)):

            return dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id,
                entry_type=dr.DeviceEntryType.SERVICE,
                identifiers={(DOMAIN, hue_resource.id)},
                name=hue_resource.metadata.name,
                model=hue_resource.type.value.replace("_", " ").title(),
                manufacturer=api.config.bridge_device.product_data.manufacturer_name,
                via_device=(DOMAIN, api.config.bridge_device.id),
                suggested_area=hue_resource.metadata.name
                if hue_resource.type == ResourceTypes.ROOM
                else None,
            )

        params = {
            ATTR_IDENTIFIERS: {(DOMAIN, hue_resource.id)},
            ATTR_SW_VERSION: hue_resource.product_data.software_version,
            ATTR_NAME: hue_resource.metadata.name,
            ATTR_MODEL: hue_resource.product_data.product_name,
            ATTR_MODEL_ID: hue_resource.product_data.model_id,
            ATTR_MANUFACTURER: hue_resource.product_data.manufacturer_name,
        }
        if room := dev_controller.get_room(hue_resource.id):
            params[ATTR_SUGGESTED_AREA] = room.metadata.name
        if hue_resource.id == api.config.bridge_device.id:
            params[ATTR_IDENTIFIERS].add((DOMAIN, api.config.bridge_id))
        else:
            params[ATTR_VIA_DEVICE] = (DOMAIN, api.config.bridge_device.id)
        zigbee = dev_controller.get_zigbee_connectivity(hue_resource.id)
        if zigbee and zigbee.mac_address:
            params[ATTR_CONNECTIONS] = {(dr.CONNECTION_NETWORK_MAC, zigbee.mac_address)}

        return dev_reg.async_get_or_create(config_entry_id=entry.entry_id, **params)

    @callback
    def remove_device(hue_device_id: str) -> None:

        if device := dev_reg.async_get_device(identifiers={(DOMAIN, hue_device_id)}):

            dev_reg.async_remove_device(device.id)

    @callback
    def handle_device_event(
        evt_type: EventType, hue_resource: Device | Room | Zone | ServiceGroup
    ) -> None:

        if evt_type == EventType.RESOURCE_DELETED:
            remove_device(hue_resource.id)
        else:

            add_device(hue_resource)



    hue_devices = list(dev_controller)
    hue_devices.sort(key=lambda dev: dev.id != api.config.bridge_device.id)
    known_devices = [add_device(hue_device) for hue_device in hue_devices]
    known_devices += [add_device(hue_room) for hue_room in api.groups.room]
    known_devices += [add_device(hue_zone) for hue_zone in api.groups.zone]
    known_devices += [add_device(sg) for sg in api.config.service_group]


    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if device not in known_devices:
            dev_reg.async_remove_device(device.id)


    entry.async_on_unload(dev_controller.subscribe(handle_device_event))
    entry.async_on_unload(api.groups.room.subscribe(handle_device_event))
    entry.async_on_unload(api.groups.zone.subscribe(handle_device_event))
    entry.async_on_unload(api.config.service_group.subscribe(handle_device_event))
