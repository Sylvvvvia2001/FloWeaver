

from __future__ import annotations

import functools

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import ZHAEntity
from .helpers import (
    SIGNAL_ADD_ENTITIES,
    async_add_entities as zha_async_add_entities,
    get_zha_data,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    zha_data = get_zha_data(hass)
    entities_to_create = zha_data.platforms[Platform.DEVICE_TRACKER]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            zha_async_add_entities,
            async_add_entities,
            ZHADeviceScannerEntity,
            entities_to_create,
        ),
    )
    config_entry.async_on_unload(unsub)


class ZHADeviceScannerEntity(ScannerEntity, ZHAEntity):


    _attr_should_poll = True
    _attr_name: str = "Device scanner"

    @property
    def is_connected(self) -> bool:

        return self.entity_data.entity.is_connected

    @property
    def battery_level(self) -> int | None:




        return self.entity_data.entity.battery_level

    @property
    def device_info(self) -> DeviceInfo:



        return ZHAEntity.device_info.__get__(self)

    @property
    def unique_id(self) -> str:


        return ZHAEntity.unique_id.__get__(self)
