

from __future__ import annotations

from functools import partial

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.config import (
    EntertainmentConfiguration,
    EntertainmentConfigurationController,
)
from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.sensors import (
    CameraMotionController,
    ContactController,
    GroupedMotionController,
    MotionController,
    SecurityAreaMotionController,
    TamperController,
)
from aiohue.v2.models.camera_motion import CameraMotion
from aiohue.v2.models.contact import Contact, ContactState
from aiohue.v2.models.entertainment_configuration import EntertainmentStatus
from aiohue.v2.models.grouped_motion import GroupedMotion
from aiohue.v2.models.motion import Motion
from aiohue.v2.models.resource import ResourceTypes
from aiohue.v2.models.security_area_motion import SecurityAreaMotion
from aiohue.v2.models.tamper import Tamper, TamperState

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ..bridge import HueBridge, HueConfigEntry
from ..const import DOMAIN
from .entity import HueBaseEntity

type SensorType = (
    CameraMotion
    | Contact
    | Motion
    | EntertainmentConfiguration
    | Tamper
    | GroupedMotion
    | SecurityAreaMotion
)
type ControllerType = (
    CameraMotionController
    | ContactController
    | MotionController
    | EntertainmentConfigurationController
    | TamperController
    | GroupedMotionController
    | SecurityAreaMotionController
)


def _resource_valid(resource: SensorType, controller: ControllerType) -> bool:

    if isinstance(resource, GroupedMotion):

        if resource.owner.rtype not in (
            ResourceTypes.ROOM,
            ResourceTypes.ZONE,
            ResourceTypes.SERVICE_GROUP,
        ):
            return False

        if not (parent := controller.get_parent(resource.id)):
            return False


        if len(parent.children) <= 1:
            return False

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    bridge = config_entry.runtime_data
    api: HueBridgeV2 = bridge.api

    @callback
    def register_items(controller: ControllerType, sensor_class: SensorType):
        make_binary_sensor_entity = partial(sensor_class, bridge, controller)

        @callback
        def async_add_sensor(event_type: EventType, resource: SensorType) -> None:

            if not _resource_valid(resource, controller):
                return
            async_add_entities([make_binary_sensor_entity(resource)])


        async_add_entities(
            make_binary_sensor_entity(sensor)
            for sensor in controller
            if _resource_valid(sensor, controller)
        )


        config_entry.async_on_unload(
            controller.subscribe(
                async_add_sensor, event_filter=EventType.RESOURCE_ADDED
            )
        )


    register_items(api.sensors.camera_motion, HueMotionSensor)
    register_items(api.sensors.motion, HueMotionSensor)
    register_items(api.config.entertainment_configuration, HueEntertainmentActiveSensor)
    register_items(api.sensors.contact, HueContactSensor)
    register_items(api.sensors.tamper, HueTamperSensor)
    register_items(api.sensors.grouped_motion, HueGroupedMotionSensor)
    register_items(api.sensors.security_area_motion, HueMotionAwareSensor)



class HueMotionSensor(HueBaseEntity, BinarySensorEntity):


    controller: CameraMotionController | MotionController
    resource: CameraMotion | Motion

    entity_description = BinarySensorEntityDescription(
        key="motion_sensor",
        device_class=BinarySensorDeviceClass.MOTION,
        has_entity_name=True,
    )

    @property
    def is_on(self) -> bool | None:

        if not self.resource.enabled:

            return None
        if not (motion_feature := self.resource.motion):
            return None
        if motion_feature.motion_report is not None:
            return motion_feature.motion_report.motion
        return motion_feature.motion



class HueGroupedMotionSensor(HueMotionSensor):


    controller: GroupedMotionController
    resource: GroupedMotion

    def __init__(
        self,
        bridge: HueBridge,
        controller: GroupedMotionController,
        resource: GroupedMotion,
    ) -> None:

        super().__init__(bridge, controller, resource)


        parent = self.controller.get_parent(resource.id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, parent.id)},
        )



class HueMotionAwareSensor(HueMotionSensor):









    controller: SecurityAreaMotionController
    resource: SecurityAreaMotion

    entity_description = BinarySensorEntityDescription(
        key="motion_sensor",
        device_class=BinarySensorDeviceClass.MOTION,
        has_entity_name=False,
    )

    @property
    def name(self) -> str:

        return self.controller.get_motion_area_configuration(self.resource.id).name

    def __init__(
        self,
        bridge: HueBridge,
        controller: SecurityAreaMotionController,
        resource: SecurityAreaMotion,
    ) -> None:

        super().__init__(bridge, controller, resource)

        self._motion_area_configuration = self.controller.get_motion_area_configuration(
            resource.id
        )
        group_id = self._motion_area_configuration.group.rid
        self.hue_group = self.bridge.api.groups[group_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.hue_group.id)},
        )

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()

        self.async_on_remove(
            self.bridge.api.config.subscribe(
                self._handle_event, self._motion_area_configuration.id
            )
        )



class HueEntertainmentActiveSensor(HueBaseEntity, BinarySensorEntity):


    controller: EntertainmentConfigurationController
    resource: EntertainmentConfiguration

    entity_description = BinarySensorEntityDescription(
        key="entertainment_active_sensor",
        device_class=BinarySensorDeviceClass.RUNNING,
        has_entity_name=False,
    )

    @property
    def is_on(self) -> bool | None:

        return self.resource.status == EntertainmentStatus.ACTIVE

    @property
    def name(self) -> str:

        return self.resource.metadata.name



class HueContactSensor(HueBaseEntity, BinarySensorEntity):


    controller: ContactController
    resource: Contact

    entity_description = BinarySensorEntityDescription(
        key="contact_sensor",
        device_class=BinarySensorDeviceClass.OPENING,
        has_entity_name=True,
    )

    @property
    def is_on(self) -> bool | None:

        if not self.resource.enabled:

            return None
        return self.resource.contact_report.state != ContactState.CONTACT



class HueTamperSensor(HueBaseEntity, BinarySensorEntity):


    controller: TamperController
    resource: Tamper

    entity_description = BinarySensorEntityDescription(
        key="tamper_sensor",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    )

    @property
    def is_on(self) -> bool | None:

        if not self.resource.tamper_reports:
            return False
        return self.resource.tamper_reports[0].state == TamperState.TAMPERED
