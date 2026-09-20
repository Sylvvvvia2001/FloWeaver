

from homeassistant.helpers import entity
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import CONF_ALLOW_UNREACHABLE, DEFAULT_ALLOW_UNREACHABLE, DOMAIN


class GenericHueDevice(entity.Entity):


    def __init__(self, sensor, name, bridge, primary_sensor=None):

        self.sensor = sensor
        self._name = name
        self._primary_sensor = primary_sensor
        self.bridge = bridge
        self.allow_unreachable = bridge.config_entry.options.get(
            CONF_ALLOW_UNREACHABLE, DEFAULT_ALLOW_UNREACHABLE
        )

    @property
    def primary_sensor(self):

        return self._primary_sensor or self.sensor

    @property
    def device_id(self):

        return self.unique_id[:23]

    @property
    def unique_id(self):

        return self.sensor.uniqueid

    @property
    def name(self):

        return self._name

    @property
    def swupdatestate(self):

        return self.primary_sensor.raw.get("swupdate", {}).get("state")

    @property
    def device_info(self) -> DeviceInfo:




        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer=self.primary_sensor.manufacturername,
            model=(self.primary_sensor.productname or self.primary_sensor.modelid),
            name=self.primary_sensor.name,
            sw_version=self.primary_sensor.swversion,
            via_device=(DOMAIN, self.bridge.api.config.bridgeid),
        )
