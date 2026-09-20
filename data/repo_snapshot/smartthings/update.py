

from __future__ import annotations

from typing import Any

from awesomeversion import AwesomeVersion
from pysmartthings import Attribute, Capability, Command

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartThingsConfigEntry
from .const import MAIN
from .entity import SmartThingsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartThingsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    entry_data = entry.runtime_data
    async_add_entities(
        SmartThingsUpdateEntity(entry_data.client, device, {Capability.FIRMWARE_UPDATE})
        for device in entry_data.devices.values()
        if Capability.FIRMWARE_UPDATE in device.status[MAIN]
    )


def is_hex_version(version: str) -> bool:

    return len(version) == 8 and all(c in "0123456789abcdefABCDEF" for c in version)


class SmartThingsUpdateEntity(SmartThingsEntity, UpdateEntity):


    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
    )

    @property
    def installed_version(self) -> str | None:

        return self.get_attribute_value(
            Capability.FIRMWARE_UPDATE, Attribute.CURRENT_VERSION
        )

    @property
    def latest_version(self) -> str | None:

        return self.get_attribute_value(
            Capability.FIRMWARE_UPDATE, Attribute.AVAILABLE_VERSION
        )

    @property
    def in_progress(self) -> bool:

        return (
            self.get_attribute_value(Capability.FIRMWARE_UPDATE, Attribute.STATE)
            == "updateInProgress"
        )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:

        await self.execute_device_command(
            Capability.FIRMWARE_UPDATE,
            Command.UPDATE_FIRMWARE,
        )

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:

        if is_hex_version(latest_version):
            latest_version = f"0x{latest_version}"
        if is_hex_version(installed_version):
            installed_version = f"0x{installed_version}"
        return AwesomeVersion(latest_version) > AwesomeVersion(installed_version)
