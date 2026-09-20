

from __future__ import annotations

from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.characteristics.const import InputEventValues
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.utils import clamp_enum_to_char

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import BaseCharacteristicEntity

INPUT_EVENT_VALUES = {
    InputEventValues.SINGLE_PRESS: "single_press",
    InputEventValues.DOUBLE_PRESS: "double_press",
    InputEventValues.LONG_PRESS: "long_press",
}


class HomeKitEventEntity(BaseCharacteristicEntity, EventEntity):


    _attr_should_poll = False

    def __init__(
        self,
        connection: HKDevice,
        service: Service,
        entity_description: EventEntityDescription,
    ) -> None:

        super().__init__(
            connection,
            {
                "aid": service.accessory.aid,
                "iid": service.iid,
            },
            service.characteristics_by_type[CharacteristicsTypes.INPUT_EVENT],
        )

        self.entity_description = entity_description



        self._attr_event_types = [
            INPUT_EVENT_VALUES[v]
            for v in clamp_enum_to_char(InputEventValues, self._char)
        ]

    def get_characteristic_types(self) -> list[str]:

        return [CharacteristicsTypes.INPUT_EVENT]

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()

        self.async_on_remove(
            self._accessory.async_subscribe(
                {(self._aid, self._char.iid)},
                self._handle_event,
            )
        )

    @callback
    def _handle_event(self) -> None:
        if self._char.value is None:



            return
        self._trigger_event(INPUT_EVENT_VALUES[self._char.value])
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_service(service: Service) -> bool:
        entities = []

        if service.type == ServicesTypes.DOORBELL:
            entities.append(
                HomeKitEventEntity(
                    conn,
                    service,
                    EventEntityDescription(
                        key=f"{service.accessory.aid}_{service.iid}",
                        device_class=EventDeviceClass.DOORBELL,
                        translation_key="doorbell",
                    ),
                )
            )

        elif service.type == ServicesTypes.SERVICE_LABEL:
            switches = list(
                service.accessory.services.filter(
                    service_type=ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH,
                    child_service=service,
                    order_by=[CharacteristicsTypes.SERVICE_LABEL_INDEX],
                )
            )




            entities.extend(
                HomeKitEventEntity(
                    conn,
                    switch,
                    EventEntityDescription(
                        key=f"{service.accessory.aid}_{service.iid}",
                        device_class=EventDeviceClass.BUTTON,
                        translation_key="button",
                    ),
                )
                for switch in switches
            )

        elif service.type == ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH:


            if not service.has(CharacteristicsTypes.SERVICE_LABEL_INDEX):
                entities.append(
                    HomeKitEventEntity(
                        conn,
                        service,
                        EventEntityDescription(
                            key=f"{service.accessory.aid}_{service.iid}",
                            device_class=EventDeviceClass.BUTTON,
                            translation_key="button",
                        ),
                    )
                )

        if entities:
            async_add_entities(entities)
            return True

        return False

    conn.add_listener(async_add_service)
