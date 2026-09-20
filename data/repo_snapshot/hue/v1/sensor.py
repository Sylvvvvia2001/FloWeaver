

from typing import Any

from aiohue.v1.sensors import (
    TYPE_ZLL_LIGHTLEVEL,
    TYPE_ZLL_ROTARY,
    TYPE_ZLL_SWITCH,
    TYPE_ZLL_TEMPERATURE,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import LIGHT_LUX, PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ..bridge import HueConfigEntry
from .sensor_base import SENSOR_CONFIG_MAP, GenericHueSensor, GenericZLLSensor

LIGHT_LEVEL_NAME_FORMAT = "{} light level"
REMOTE_NAME_FORMAT = "{} battery level"
TEMPERATURE_NAME_FORMAT = "{} temperature"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    bridge = config_entry.runtime_data

    if not bridge.sensor_manager:
        return

    await bridge.sensor_manager.async_register_component("sensor", async_add_entities)



class GenericHueGaugeSensorEntity(GenericZLLSensor, SensorEntity):
    pass



class HueLightLevel(GenericHueGaugeSensorEntity):


    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX

    @property
    def native_value(self):

        if self.sensor.lightlevel is None:
            return None






        return round(float(10 ** ((self.sensor.lightlevel - 1) / 10000)), 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:

        attributes = super().extra_state_attributes
        attributes.update(
            {
                "lightlevel": self.sensor.lightlevel,
                "daylight": self.sensor.daylight,
                "dark": self.sensor.dark,
                "threshold_dark": self.sensor.tholddark,
                "threshold_offset": self.sensor.tholdoffset,
            }
        )
        return attributes



class HueTemperature(GenericHueGaugeSensorEntity):


    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):

        if self.sensor.temperature is None:
            return None

        return self.sensor.temperature / 100



class HueBattery(GenericHueSensor, SensorEntity):


    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):

        return f"{self.sensor.uniqueid}-battery"

    @property
    def native_value(self):

        return self.sensor.battery


SENSOR_CONFIG_MAP.update(
    {
        TYPE_ZLL_LIGHTLEVEL: {
            "platform": "sensor",
            "name_format": LIGHT_LEVEL_NAME_FORMAT,
            "class": HueLightLevel,
        },
        TYPE_ZLL_TEMPERATURE: {
            "platform": "sensor",
            "name_format": TEMPERATURE_NAME_FORMAT,
            "class": HueTemperature,
        },
        TYPE_ZLL_SWITCH: {
            "platform": "sensor",
            "name_format": REMOTE_NAME_FORMAT,
            "class": HueBattery,
        },
        TYPE_ZLL_ROTARY: {
            "platform": "sensor",
            "name_format": REMOTE_NAME_FORMAT,
            "class": HueBattery,
        },
    }
)
