

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EcobeeConfigEntry, EcobeeData
from .entity import EcobeeBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EcobeeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    data = config_entry.runtime_data
    async_add_entities(
        EcobeeNotifyEntity(data, index) for index in range(len(data.ecobee.thermostats))
    )


class EcobeeNotifyEntity(EcobeeBaseEntity, NotifyEntity):


    _attr_name = None
    _attr_has_entity_name = True

    def __init__(self, data: EcobeeData, thermostat_index: int) -> None:

        super().__init__(data, thermostat_index)
        self._attr_unique_id = (
            f"{self.thermostat['identifier']}_notify_{thermostat_index}"
        )

    def send_message(self, message: str, title: str | None = None) -> None:

        self.data.ecobee.send_message(self.thermostat_index, message)
