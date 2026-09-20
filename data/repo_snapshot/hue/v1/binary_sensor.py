

from typing import Any

from aiohue.v1.sensors import TYPE_ZLL_PRESENCE

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ..bridge import HueConfigEntry
from .sensor_base import SENSOR_CONFIG_MAP, GenericZLLSensor

PRESENCE_NAME_FORMAT = "{} motion"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    bridge = config_entry.runtime_data

    if not bridge.sensor_manager:
        return

    await bridge.sensor_manager.async_register_component(
        "binary_sensor", async_add_entities
    )



class HuePresence(GenericZLLSensor, BinarySensorEntity):


    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool:

        return self.sensor.presence

    @property
    def extra_state_attributes(self) -> dict[str, Any]:

        attributes = super().extra_state_attributes
        if "sensitivity" in self.sensor.config:
            attributes["sensitivity"] = self.sensor.config["sensitivity"]
        if "sensitivitymax" in self.sensor.config:
            attributes["sensitivity_max"] = self.sensor.config["sensitivitymax"]
        return attributes


SENSOR_CONFIG_MAP.update(
    {
        TYPE_ZLL_PRESENCE: {
            "platform": "binary_sensor",
            "name_format": PRESENCE_NAME_FORMAT,
            "class": HuePresence,
        }
    }
)
