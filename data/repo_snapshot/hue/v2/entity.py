

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohue.v2.controllers.base import BaseResourcesController
from aiohue.v2.controllers.events import EventType
from aiohue.v2.models.resource import ResourceTypes
from aiohue.v2.models.zigbee_connectivity import ConnectivityServiceStatus

from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from ..bridge import HueBridge
from ..const import CONF_IGNORE_AVAILABILITY, DOMAIN

if TYPE_CHECKING:
    from aiohue.v2.models.device_power import DevicePower
    from aiohue.v2.models.grouped_light import GroupedLight
    from aiohue.v2.models.light import Light
    from aiohue.v2.models.light_level import LightLevel
    from aiohue.v2.models.motion import Motion

    type HueResource = Light | DevicePower | GroupedLight | LightLevel | Motion


RESOURCE_TYPE_NAMES = {

    ResourceTypes.LIGHT_LEVEL: "Illuminance",
    ResourceTypes.DEVICE_POWER: "Battery",
}


class HueBaseEntity(Entity):


    _attr_should_poll = False

    def __init__(
        self,
        bridge: HueBridge,
        controller: BaseResourcesController,
        resource: HueResource,
    ) -> None:

        self.bridge = bridge
        self.controller = controller
        self.resource = resource
        self.device = controller.get_device(resource.id)
        self.logger = bridge.logger.getChild(resource.type.value)


        self._attr_unique_id = resource.id


        if self.device is None:


            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, bridge.api.config.bridge.bridge_id)},
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self.device.id)},
            )

        self._ignore_availability = None
        self._last_state = None

    async def async_added_to_hass(self) -> None:

        self._check_availability()

        self.async_on_remove(
            self.controller.subscribe(
                self._handle_event,
                self.resource.id,
                (EventType.RESOURCE_UPDATED, EventType.RESOURCE_DELETED),
            )
        )

        if self.device is None:
            return
        self.async_on_remove(
            self.bridge.api.devices.subscribe(
                self._handle_event,
                self.device.id,
                EventType.RESOURCE_UPDATED,
            )
        )

        if zigbee := self.bridge.api.devices.get_zigbee_connectivity(self.device.id):
            self.async_on_remove(
                self.bridge.api.sensors.zigbee_connectivity.subscribe(
                    self._handle_event,
                    zigbee.id,
                    EventType.RESOURCE_UPDATED,
                )
            )

    @property
    def available(self) -> bool:


        if self.device is None:
            return True

        if self.resource.type == ResourceTypes.ZIGBEE_CONNECTIVITY:
            return True
        if self._ignore_availability:
            return True

        if zigbee := self.bridge.api.devices.get_zigbee_connectivity(self.device.id):
            return zigbee.status == ConnectivityServiceStatus.CONNECTED
        return True

    @callback
    def on_update(self) -> None:
        pass


    @callback
    def _handle_event(self, event_type: EventType, resource: HueResource) -> None:

        if event_type == EventType.RESOURCE_DELETED:

            if self.device is None and resource.id == self.resource.id:
                ent_reg = er.async_get(self.hass)
                ent_reg.async_remove(self.entity_id)
            return

        self.logger.debug("Received status update for %s", self.entity_id)
        self._check_availability()
        self.on_update()
        self.async_write_ha_state()

    @callback
    def _check_availability(self):


        if self._ignore_availability is not None:
            return

        if self.device is None or not hasattr(self.resource, "on"):
            self._ignore_availability = False
            return

        if self.device.id in self.bridge.config_entry.options.get(
            CONF_IGNORE_AVAILABILITY, []
        ):
            self._ignore_availability = True
            self.logger.info(
                "Device %s is configured to ignore availability status. ",
                self.name,
            )
            return


        if self.device.product_data.certified:
            self._ignore_availability = False
            return







        cur_state = self.resource.on.on
        if self._last_state is None:
            self._last_state = cur_state
            return
        if zigbee := self.bridge.api.devices.get_zigbee_connectivity(self.device.id):
            if (
                self._last_state != cur_state
                and zigbee.status != ConnectivityServiceStatus.CONNECTED
            ):


                self.logger.warning(
                    (
                        "Device %s changed state while reported as disconnected. This"
                        " might be an indicator that routing is not working for this"
                        " device or the device is having connectivity issues. You can"
                        " disable availability reporting for this device in the Hue"
                        " options. Device details: %s - %s (%s) fw: %s"
                    ),
                    self.name,
                    self.device.product_data.manufacturer_name,
                    self.device.product_data.product_name,
                    self.device.product_data.model_id,
                    self.device.product_data.software_version,
                )


                self._ignore_availability = False
        self._last_state = cur_state
