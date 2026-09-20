

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rokuecp.models import Device as RokuDevice

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RokuConfigEntry
from .entity import RokuEntity


PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class RokuBinarySensorEntityDescription(BinarySensorEntityDescription):


    value_fn: Callable[[RokuDevice], bool | None]


BINARY_SENSORS: tuple[RokuBinarySensorEntityDescription, ...] = (
    RokuBinarySensorEntityDescription(
        key="headphones_connected",
        translation_key="headphones_connected",
        value_fn=lambda device: device.info.headphones_connected,
    ),
    RokuBinarySensorEntityDescription(
        key="supports_airplay",
        translation_key="supports_airplay",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.info.supports_airplay,
    ),
    RokuBinarySensorEntityDescription(
        key="supports_ethernet",
        translation_key="supports_ethernet",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.info.ethernet_support,
    ),
    RokuBinarySensorEntityDescription(
        key="supports_find_remote",
        translation_key="supports_find_remote",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.info.supports_find_remote,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RokuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_add_entities(
        RokuBinarySensorEntity(
            coordinator=entry.runtime_data,
            description=description,
        )
        for description in BINARY_SENSORS
    )


class RokuBinarySensorEntity(RokuEntity, BinarySensorEntity):


    entity_description: RokuBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:

        return self.entity_description.value_fn(self.coordinator.data)
