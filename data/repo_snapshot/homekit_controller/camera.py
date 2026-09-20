

from __future__ import annotations

from aiohomekit.model import Accessory
from aiohomekit.model.services import ServicesTypes

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import AccessoryEntity


class HomeKitCamera(AccessoryEntity, Camera):




    def get_characteristic_types(self) -> list[str]:

        return []

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:

        return await self._accessory.pairing.image(
            self._aid,
            width or 640,
            height or 480,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_accessory(accessory: Accessory) -> bool:
        stream_mgmt = accessory.services.first(
            service_type=ServicesTypes.CAMERA_RTP_STREAM_MANAGEMENT
        )
        if not stream_mgmt:
            return False

        info = {"aid": accessory.aid, "iid": stream_mgmt.iid}
        entity = HomeKitCamera(conn, info)
        conn.async_migrate_unique_id(
            entity.old_unique_id, entity.unique_id, Platform.CAMERA
        )
        async_add_entities([entity])
        return True

    conn.add_accessory_factory(async_add_accessory)
