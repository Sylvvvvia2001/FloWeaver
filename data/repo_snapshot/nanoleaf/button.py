

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoleafConfigEntry, NanoleafCoordinator
from .entity import NanoleafEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NanoleafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_add_entities([NanoleafIdentifyButton(entry.runtime_data)])


class NanoleafIdentifyButton(NanoleafEntity, ButtonEntity):


    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = ButtonDeviceClass.IDENTIFY

    def __init__(self, coordinator: NanoleafCoordinator) -> None:

        super().__init__(coordinator)
        self._attr_unique_id = f"{self._nanoleaf.serial_no}_identify"

    async def async_press(self) -> None:

        await self._nanoleaf.identify()
